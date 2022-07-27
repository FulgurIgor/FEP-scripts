# Работа со скриптом FEP_pmx_db.py


## Подготовка

Все действия выполняются с Python 3. Проверялось на HPC4 с модулем `anaconda3/python3-5.1.0`.

На HPC4 модуль можно загрузить командой:
```bash
module load anaconda3/python3-5.1.0
```

Клонирование репозитария:
```
git clone git@github.com:FulgurIgor/FEP-scripts.git
```

### Установка pmx

[pmx](https://github.com/deGrootLab/pmx) устанавливается только для используемого пользователя, то есть при переносе на другой аккаунт/машину, действия придется повторить.
Здесь используется версия pmx, основанная на Python 3. Она находится в ветке `develop` вышеуказанного репозитария.

В случае HPC4, необходимо применение патча, так как на нем используется старая версия `git`.

Установка выполняется выполнением команды:
```bash
bash pmx-install.sh
```
Убедитесь, что файл `0001-Fix-for-old-git.patch` находится в одной папке со скриптом `pmx-install.sh`.

После этого pmx установлен.
Проверку работоспособности pmx можно выполнить, запустив скрипт `analyze_dhdl.py` (необходимо взять его в `pmx/src/pmx/scripts/` после установки pmx).


### Расположение папок и файлов

Рядом с `FEP_pmx_db.py` должны находиться скрипты `analyze_dhdl.py` (можно взять в `pmx/src/pmx/scripts/` после установки pmx), `extract.py` и `extract2csv.sh`.

Файл базы данных (о нём чуть ниже) должен находиться в папке с папками для расчетов (белков или что там, я не знаю).

Структура файлов и папок может выгдядеть как-то так:
```
root/
├── FEP_pmx_db.py
├── analyze_dhdl.py
├── extract.py
├── extract2csv.sh
├── calc_1/
│   ├── cdk5/
│   │   └── ###            Files for calc
│   ├── cdk6/
│   │   └── ###            Files for calc
│   └── FEP.db             Database file
└── calc_2/
    ├── cdk1/
    │   └── ###            Files for calc
    ├── cdk2/
    │   └── ###            Files for calc
    └── FEP.db             Database file
```


## Запуск задач

Запуск скрипта `FEP_pmx_db.py` с флагом `--help` выводит список всех доступных флагов. Ниже разберем их подробнее.
```
$ ./FEP_pmx_db.py --help
usage: FEP_pmx_db.py [-h] --db DB [--add ADD] [--stage STAGE] [--remove REMOVE] [--force] [--run] [--dump] [--dump_csv DUMP_CSV]

FEB database

options:
  -h, --help           show this help message and exit
  --db DB              Database file; must be in working directory (default: None)
  --add ADD            directories that will be added to calculations' list; comma separator is used (default: None)
  --stage STAGE        stages of calculations that will be added to calculations' list; comma separator is used (default: None)
  --remove REMOVE      folders that will be removed from calculations' list; comma separator is used (default: None)
  --force              Forces updating of tasks (default: False)
  --run                Run one step for all tasks (default: False)
  --dump               Dump database (default: False)
  --dump_csv DUMP_CSV  Dump database to file (default: None)
```


### --db

Данный флаг является обязательным и указывает на путь к файлу с базой данных (создается при необходимости).
Рядом с этим файлом должны находиться папки с расчетами.

Пример использования:
```bash
$ ./FEP_pmx_db.py --db calc_1/FEP.db
```


### --add ADD

**Используется всегда с `--stage`**

Добавляет папку в очередь расчетов. Этап расчета определяется флагом `--stage`.

Возможно указание нескольких папок через запятую (как в примере).
Расшифровку `--stage` смотри ниже.

Пример использования:
```bash
$ ./FEP_pmx_db.py --db calc_1/FEP.db --add cdk5,cdk6 --stage 1,4
```

Здесь cdk5 будет считаться с 1 этапа, cdk6 --- с 4-ого.

Для перезаписи уже идущих задач необходимо использовать флаг `--force` (возможно, не всегда корректно отрабатывает).


### --stage STAGE

**Используется всегда с `--add`**

Указывает на этап, который будет использоваться для расчета соответствующей папки.

Этапы:
* 1 - MD preparation
* 2 - MD
* 3 - FEP preparation
* 4 - FEP
* 5 - Result processing

Скрипт не понимает слов, только цифры.
Про расшифровку этапов написано ниже.

Пример использования:
```bash
$ ./FEP_pmx_db.py --db calc_1/FEP.db --add cdk5,cdk6 --stage 1,4
```

Здесь cdk5 будет считаться с 1 этапа, cdk6 --- с 4-ого.


### --remove REMOVE

Удаляет папку из расчетов.

Пример использования:
```bash
$ ./FEP_pmx_db.py --db calc_1/FEP.db --remove cdk5
```

Останавливает вычисление FEP для cdk5.

Если задача находится в очереди (статус `Waiting...`), то для удаления такой задачи необходимо добавить флаг `--force`.


### --force

Используется для флагов `--add` и `--remove`, если существует вероятность что-либо сломать.

Пример использования:
```bash
$ ./FEP_pmx_db.py --db calc_1/FEP.db --add cdk5 --stage 4
$ ./FEP_pmx_db.py --db calc_1/FEP.db --run
$ ./FEP_pmx_db.py --db calc_1/FEP.db --remove cdk5 --force
```

Добавляем расчет cdk5 с 4-ой стадии, запускаем его (стоит в очереди), для удаления используем флаг `--force`, чтобы удалить задачу из очереди.


### --run

Проверяет возможность, и если возможно, запускает следующие этапы расчетов.

Пример использования:
```bash
$ ./FEP_pmx_db.py --db calc_1/FEP.db --run
```

За один запуск проходится не более чем одна стадия расчетов.
Есть смысл создать небольшой скриптик, который раз в час (или больше по времени), будет выполнять данную команду.


### --dump

Выводит текущее состояние расчетов в консоль.

Пример использования:
```bash
$ ./FEP_pmx_db.py --db calc_1/FEP.db --dump
```


### --dump_csv DUMP_CSV

Выводит текущее состояние расчетов в файл.

Пример использования:
```bash
$ ./FEP_pmx_db.py --db calc_1/FEP.db --dump_csv calc_1/FEP.csv
```


## Этапы расчетов

### MD preparation (1)

Выполняет первоначальную подготовку файлов.
Создает директории `result_protein`, `stateA_protein` и другие.
Производит какие-то первоначальные манипуляции.

Генерируемый скрипт: `MD_preparation.sh`. Запускается из папки с расчетами `bash MD_preparation.sh`.


### MD (2)

Запускает молекулярную динамику.

Генерируемый скрипт: `MD.sh`. Запускается из папки с расчетами `sbatch MD.sh`.

Параметры SLURM скрипта:
* задач на ноду        ---  1
* используется нод     ---  1
* число OpenMP потоков --- 24

### FEP preparation (3)

Подготавливает файлы для расчета FEP.

Генерируемый скрипт: `FEP_preparation.sh`. Запускается из папки с расчетами `bash FEP_preparation.sh`.


### FEP (4)

Расчет FEP (100 траекторий, индексы 0-99).

Расчет выполняется с помощью Job Arrays, из-за чего могут возникнуть проблемы при использовании с большим числом FEP.

Генерируемый скрипт: `FEP.sh`. Запускается из папки с расчетами `sbatch --array 0-4 FEP.sh`.

Параметры SLURM скрипта:
* задач на ноду        ---  4
* используется нод     --- 25 (суммарно), 5 (для каждой задачи в Job Array).
* число OpenMP потоков ---  6


### Result processing (5)

Обработка результатов FEP.

Генерируемый скрипт: `Result_processing.sh`. Запускается из папки с расчетами `bash Result_processing.sh`.

Повляются файлы `result_TASK.csv` рядом с файлом базы данных.


### Склеивание данных

Запуская скрипт `./extract2csv.sh <directory>` с папкой, где находятся `result_TASK.csv`, генерируется файл `results.csv`, в котором суммаризированы результаты по всем белкам.


## Ограничения

* Нет обработки ошибок, поэтому скрипт будет делать фигню, если случайно где-то что-то сделано неправильно при подготовке данных.
* Текущая вариация стадии FEP не протестирована.
* `--add` + `--force` могут некорректно обрабатывать завершение задач.
