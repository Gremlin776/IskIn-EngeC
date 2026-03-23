"""
Сервис для предиктивного обслуживания
"""

from datetime import date, datetime, timedelta
from typing import Any
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.models.predictive import FailurePrediction, MaintenanceHistory
from src.core.logging import get_logger
from src.ml.predictive.forecaster import PredictiveForecaster

logger = get_logger(__name__)


class PredictiveService:
    """
    Сервис для предиктивного анализа и прогнозирования поломок.
    
    Бизнес-логика:
    - Анализ истории обслуживания
    - Прогнозирование поломок
    - Оценка рисков
    - Генерация рекомендаций
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.forecaster = PredictiveForecaster()

    async def predict_failure(
        self,
        entity_type: str,
        entity_id: int,
        equipment_type: str | None = None,
    ) -> FailurePrediction:
        """
        Прогнозирование поломки для объекта.
        
        Args:
            entity_type: Тип объекта ('premise', 'meter', 'equipment')
            entity_id: ID объекта
            equipment_type: Тип оборудования (опционально)
        
        Returns:
            Объект прогноза
        """
        # Сбор исторических данных
        history = await self._get_maintenance_history(
            entity_type, entity_id
        )

        # Прогнозирование
        prediction_data = await self.forecaster.predict(history)

        # Создание прогноза
        prediction = await self._create_prediction(
            entity_type=entity_type,
            entity_id=entity_id,
            equipment_type=equipment_type,
            prediction_data=prediction_data,
        )

        logger.info(
            f"Создан прогноз поломки для {entity_type}:{entity_id}, "
            f"вероятность: {prediction_data['probability']:.2%}"
        )
        return prediction

    async def _get_maintenance_history(
        self,
        entity_type: str,
        entity_id: int,
        months: int = 12,
    ) -> list[dict[str, Any]]:
        """Получение истории обслуживания объекта"""
        cutoff_date = date.today() - timedelta(days=months * 30)

        result = await self.session.execute(
            select(MaintenanceHistory).where(
                MaintenanceHistory.entity_type == entity_type,
                MaintenanceHistory.entity_id == entity_id,
                MaintenanceHistory.event_date >= cutoff_date,
            ).order_by(MaintenanceHistory.event_date.desc())
        )
        history = result.scalars().all()

        return [
            {
                "event_type": h.event_type,
                "event_date": h.event_date,
                "description": h.description,
                "cost": float(h.cost) if h.cost else None,
                "downtime_hours": float(h.downtime_hours) if h.downtime_hours else None,
            }
            for h in history
        ]

    async def _create_prediction(
        self,
        entity_type: str,
        entity_id: int,
        equipment_type: str | None,
        prediction_data: dict[str, Any],
    ) -> FailurePrediction:
        """Создание записи прогноза в БД"""
        from sqlalchemy import insert
        
        stmt = insert(FailurePrediction).values(
            premise_id=entity_id if entity_type == "premise" else None,
            meter_id=entity_id if entity_type == "meter" else None,
            equipment_type=equipment_type,
            prediction_date=date.today(),
            failure_probability=prediction_data["probability"],
            predicted_failure_date=prediction_data.get("predicted_date"),
            confidence_level=prediction_data.get("confidence", "medium"),
            risk_factors=self._format_risk_factors(prediction_data.get("risk_factors", [])),
            recommendations=self._format_recommendations(prediction_data.get("recommendations", [])),
            model_version=prediction_data.get("model_version", "1.0"),
            is_actual=True,
        ).returning(FailurePrediction)
        
        result = await self.session.execute(stmt)
        prediction = result.scalar_one()
        await self.session.flush()
        return prediction

    def _format_risk_factors(self, risk_factors: list[str]) -> str:
        """Форматирование факторов риска"""
        if not risk_factors:
            return "Нет данных"
        return "\n".join(f"- {factor}" for factor in risk_factors)

    def _format_recommendations(self, recommendations: list[str]) -> str:
        """Форматирование рекомендаций"""
        if not recommendations:
            return "Рекомендаций нет"
        return "\n".join(f"- {rec}" for rec in recommendations)

    async def analyze_building(
        self,
        building_id: int,
    ) -> dict[str, Any]:
        """
        Комплексный анализ здания.
        
        Returns:
            Данные анализа с прогнозами и рекомендациями
        """
        from src.models.building import Premise
        from src.models.repair import RepairRequest
        from src.models.defect import DetectedDefect, Inspection

        # Получение помещений
        premises_result = await self.session.execute(
            select(Premise.id).where(Premise.building_id == building_id)
        )
        premise_ids = [row[0] for row in premises_result.all()]

        # Статистика ремонтов
        repair_result = await self.session.execute(
            select(
                func.count(RepairRequest.id),
                func.sum(RepairRequest.cost),
            ).where(
                RepairRequest.premise_id.in_(premise_ids) if premise_ids else False
            )
        )
        repair_stats = repair_result.one()

        # Статистика дефектов
        defect_result = await self.session.execute(
            select(
                func.count(DetectedDefect.id),
                func.sum(func.case(
                    (DetectedDefect.severity == "critical", 1),
                    else_=0,
                )),
            ).where(
                DetectedDefect.inspection_id.in_(
                    select(Inspection.id).where(Inspection.building_id == building_id)
                )
            )
        )
        defect_stats = defect_result.one()

        # Прогнозирование для каждого помещения
        predictions = []
        for premise_id in premise_ids[:5]:  # Ограничение для производительности
            prediction = await self.predict_failure(
                entity_type="premise",
                entity_id=premise_id,
            )
            predictions.append({
                "premise_id": premise_id,
                "probability": float(prediction.failure_probability),
                "recommendations": prediction.recommendations,
            })

        return {
            "building_id": building_id,
            "analysis_date": date.today(),
            "repair_stats": {
                "total_repairs": repair_stats[0] or 0,
                "total_cost": float(repair_stats[1] or 0),
            },
            "defect_stats": {
                "total_defects": defect_stats[0] or 0,
                "critical_defects": defect_stats[1] or 0,
            },
            "predictions": predictions,
            "overall_risk": self._calculate_overall_risk(repair_stats, defect_stats, predictions),
        }

    def _calculate_overall_risk(
        self,
        repair_stats: tuple,
        defect_stats: tuple,
        predictions: list[dict],
    ) -> str:
        """Расчёт общего уровня риска"""
        risk_score = 0

        # Фактор ремонтов
        if repair_stats[0] and repair_stats[0] > 10:
            risk_score += 2

        # Фактор критических дефектов
        if defect_stats[1] and defect_stats[1] > 0:
            risk_score += 3

        # Фактор прогнозов
        high_prob_predictions = sum(
            1 for p in predictions if p["probability"] > 0.7
        )
        risk_score += high_prob_predictions

        # Маппинг на уровень риска
        if risk_score >= 8:
            return "critical"
        elif risk_score >= 5:
            return "high"
        elif risk_score >= 3:
            return "medium"
        else:
            return "low"

    async def analyze_meter(
        self,
        meter_id: int,
    ) -> dict[str, Any]:
        """Анализ счётчика для прогнозирования поломки"""
        prediction = await self.predict_failure(
            entity_type="meter",
            entity_id=meter_id,
            equipment_type="meter",
        )

        return {
            "meter_id": meter_id,
            "prediction": {
                "probability": float(prediction.failure_probability),
                "predicted_date": prediction.predicted_failure_date,
                "confidence": prediction.confidence_level,
                "recommendations": prediction.recommendations,
            },
        }

    async def get_predictions(
        self,
        is_actual: bool = True,
        limit: int = 100,
    ) -> list[FailurePrediction]:
        """Получение списка прогнозов"""
        result = await self.session.execute(
            select(FailurePrediction)
            .where(FailurePrediction.is_actual == is_actual)
            .order_by(FailurePrediction.failure_probability.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_risk_rating_buildings(self) -> list[dict[str, Any]]:
        """Рейтинг зданий по уровню риска"""
        from src.models.building import Building

        buildings_result = await self.session.execute(
            select(Building.id, Building.name).where(Building.is_active == True)
        )
        buildings = buildings_result.all()

        ratings = []
        for building_id, name in buildings:
            analysis = await self.analyze_building(building_id)
            ratings.append({
                "building_id": building_id,
                "name": name,
                "risk_level": analysis["overall_risk"],
                "critical_defects": analysis["defect_stats"]["critical_defects"],
            })

        # Сортировка по уровню риска
        risk_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        ratings.sort(key=lambda x: risk_order.get(x["risk_level"], 4))

        return ratings

    async def get_risk_rating_equipment(self) -> list[dict[str, Any]]:
        """Рейтинг оборудования по уровню риска"""
        from src.models.meter import Meter

        meters_result = await self.session.execute(
            select(Meter.id, Meter.meter_number, Meter.meter_type_id)
            .where(Meter.is_active == True)
            .limit(50)
        )
        meters = meters_result.all()

        ratings = []
        for meter_id, number, type_id in meters:
            analysis = await self.analyze_meter(meter_id)
            ratings.append({
                "meter_id": meter_id,
                "number": number,
                "failure_probability": analysis["prediction"]["probability"],
                "predicted_date": analysis["prediction"]["predicted_date"],
            })

        # Сортировка по вероятности поломки
        ratings.sort(key=lambda x: x["failure_probability"], reverse=True)

        return ratings

    async def retrain_model(self) -> dict[str, Any]:
        """
        Переобучение модели прогнозирования.
        
        Returns:
            Результаты переобучения
        """
        # Сбор всех исторических данных
        result = await self.session.execute(
            select(MaintenanceHistory)
        )
        history = result.scalars().all()

        if len(history) < 10:
            return {
                "success": False,
                "message": "Недостаточно данных для переобучения (минимум 10 записей)",
            }

        # Переобучение модели
        train_result = await self.forecaster.retrain(list(history))

        logger.info(f"Модель переобучена: {train_result}")

        return {
            "success": True,
            "message": "Модель успешно переобучена",
            "details": train_result,
        }

    async def add_maintenance_event(
        self,
        entity_type: str,
        entity_id: int,
        event_type: str,
        event_date: date,
        description: str | None = None,
        cost: Decimal | None = None,
        downtime_hours: Decimal | None = None,
    ) -> MaintenanceHistory:
        """Добавление события обслуживания"""
        from sqlalchemy import insert
        
        stmt = insert(MaintenanceHistory).values(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            event_date=event_date,
            description=description,
            cost=cost,
            downtime_hours=downtime_hours,
        ).returning(MaintenanceHistory)
        
        result = await self.session.execute(stmt)
        event = result.scalar_one()
        await self.session.flush()
        
        logger.info(f"Добавлено событие обслуживания: {event_type} для {entity_type}:{entity_id}")
        return event
