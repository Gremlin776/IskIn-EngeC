#!/usr/bin/env python3
"""
Скрипт для распаковки скачанных ZIP-файлов датасетов.
"""

import zipfile
import os
import shutil
from pathlib import Path

# Исключения для файлов, которые не нужно извлекать
SKIP_FILES = {
    '__MACOSX',
    '.DS_Store',
    '._.DS_Store',
    'README.txt',
    'readme.txt',
    '.gitkeep'
}

def extract_zip(zip_path: Path, extract_to: Path, overwrite: bool = True):
    """Распаковать ZIP файл с проверкой содержимого."""
    if not zip_path.exists():
        print(f"❌ Файл не найден: {zip_path}")
        return False
    
    print(f"\n📦 Распаковка: {zip_path.name}")
    print(f"   → {extract_to}")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Получаем список файлов
            file_list = zip_ref.namelist()
            
            # Проверка на вложенную папку
            root_folders = set()
            for f in file_list:
                if '/' in f:
                    root_folders.add(f.split('/')[0])
                else:
                    root_folders.add(f)
            
            # Если все файлы в одной папке, извлекаем содержимое этой папки
            if len(root_folders) == 1 and list(root_folders)[0].endswith('/'):
                single_folder = list(root_folders)[0]
                print(f"   📁 Обнаружена корневая папка: {single_folder}")
                
                # Извлекаем только содержимое, без корневой папки
                for member in file_list:
                    if member.startswith(single_folder) and member != single_folder:
                        # Пропускаем системные файлы
                        if any(skip in member for skip in SKIP_FILES):
                            continue
                        
                        # Определяем целевой путь
                        relative_path = member[len(single_folder):]
                        if relative_path:
                            target_path = extract_to / relative_path.lstrip('/')
                            
                            # Создаём директорию или извлекаем файл
                            if member.endswith('/'):
                                target_path.mkdir(parents=True, exist_ok=True)
                            else:
                                target_path.parent.mkdir(parents=True, exist_ok=True)
                                with zip_ref.open(member) as source:
                                    with open(target_path, 'wb') as target:
                                        shutil.copyfileobj(source, target)
            else:
                # Обычная распаковка
                zip_ref.extractall(extract_to)
        
        print(f"   ✅ Успешно распаковано")
        
        # Удаляем ZIP файл после успешной распаковки
        if overwrite:
            zip_path.unlink()
            print(f"   🗑️ ZIP файл удалён")
        
        return True
        
    except zipfile.BadZipFile:
        print(f"   ❌ Ошибка: файл повреждён или не является ZIP")
        return False
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False


def count_files(directory: Path) -> int:
    """Посчитать количество файлов в директории."""
    count = 0
    if directory.exists():
        for item in directory.rglob('*'):
            if item.is_file():
                count += 1
    return count


def main():
    project_root = Path(__file__).parent.parent
    datasets_dir = project_root / 'datasets'
    
    print("=" * 60)
    print("🔓 РАСПАКОВКА ДАТАСЕТОВ")
    print("=" * 60)
    
    # Список ZIP файлов для распаковки
    zip_files = [
        # Дефекты
        {
            'zip': datasets_dir / 'defects' / 'sdnet2018' / 'raw' / 'SDNET2018.zip',
            'target': datasets_dir / 'defects' / 'sdnet2018' / 'raw',
            'name': 'SDNET2018'
        },
        {
            'zip': datasets_dir / 'defects' / 'roads_bridges_cracks' / 'yolo' / 'Roads and Bridges Cracks (YOLOv8 Format).zip',
            'target': datasets_dir / 'defects' / 'roads_bridges_cracks' / 'yolo',
            'name': 'Roads and Bridges Cracks (YOLOv8)'
        },
        # Энергопотребление
        {
            'zip': datasets_dir / 'energy' / 'data' / 'bdgp2' / 'Building Data Genome Project 2.zip',
            'target': datasets_dir / 'energy' / 'data' / 'bdgp2',
            'name': 'Building Data Genome Project 2'
        },
        {
            'zip': datasets_dir / 'energy' / 'data' / 'ashrae_gepii' / 'ASHRAE - Great Energy Predictor III FeatherDataset.zip',
            'target': datasets_dir / 'energy' / 'data' / 'ashrae_gepii',
            'name': 'ASHRAE GEPIII'
        },
        # ??????? ?? ????????? ?????????
        {
            'zip': datasets_dir / 'occupancy' / 'occupancy_uci' / 'Occupancy Detection Data Set UCI.zip',
            'target': datasets_dir / 'occupancy' / 'occupancy_uci',
            'name': 'Occupancy Detection UCI'
        },
        # ???????? ??? ????????????? ?????????
        {
            'zip': datasets_dir / 'ocr_readings' / 'svhn' / 'SVHN.zip',
            'target': datasets_dir / 'ocr_readings' / 'svhn',
            'name': 'SVHN'
        },
        {
            'zip': datasets_dir / 'ocr_readings' / 'water_meters' / 'Water Meters Dataset.zip',
            'target': datasets_dir / 'ocr_readings' / 'water_meters',
            'name': 'Water Meters Dataset'
        },
    ]
    
    success_count = 0
    for item in zip_files:
        if item['zip'].exists():
            if extract_zip(item['zip'], item['target']):
                success_count += 1
        else:
            print(f"\n⚠️  Не найден: {item['name']}")
            print(f"   Ожидался: {item['zip']}")
    
    print("\n" + "=" * 60)
    print("📊 СТАТИСТИКА ПО ДАТАСЕТАМ")
    print("=" * 60)
    
    # Статистика по папкам
    stats = [
        ('SDNET2018', datasets_dir / 'defects' / 'sdnet2018' / 'raw'),
        ('Roads & Bridges Cracks', datasets_dir / 'defects' / 'roads_bridges_cracks' / 'yolo'),
        ('BDGP2 (Energy)', datasets_dir / 'energy' / 'data' / 'bdgp2'),
        ('ASHRAE GEPIII', datasets_dir / 'energy' / 'data' / 'ashrae_gepii'),
        ('Occupancy UCI', datasets_dir / 'occupancy' / 'occupancy_uci'),
        ('SVHN (OCR)', datasets_dir / 'ocr_readings' / 'svhn'),
        ('Water Meters (OCR)', datasets_dir / 'ocr_readings' / 'water_meters'),
    ]
    
    for name, path in stats:
        file_count = count_files(path)
        status = "✅" if file_count > 0 else "⚠️ "
        print(f"{status} {name}: {file_count} файлов")
    
    print("\n" + "=" * 60)
    print(f"✅ Распаковано успешно: {success_count}/{len(zip_files)}")
    print("=" * 60)


if __name__ == '__main__':
    main()
