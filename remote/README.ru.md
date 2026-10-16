English version: [README.md](README.md).

# remote/ — долгие вычисления на удалённой машине

Перебор метабиблиотеки, большие резольвенты и Lean-проверка сертификатов идут часами. Их можно
отправить фоновыми задачами на любую Linux-машину с systemd и доступом по ssh («раннер»):

| Файл | Что |
|---|---|
| `mr-remote.sh` | `submit`, `status`, `log`, `fetch`, `cancel` — рабочее дерево как есть уезжает на машину и идёт там юнитом systemd |
| `setup-box.sh` | разовая подготовка машины: `uv`; с `--rust` — Rust, с `--lean` — elan, для пользователя задач |
| `py-env.sh` | окружение Python для задачи (`source remote/py-env.sh`), venv по хешу `requirements-py.txt` |

Настройка — только переменными окружения; хоста по умолчанию нет:

```bash
export MR_REMOTE_HOST=root@runner.example.org   # куда ssh; должен уметь systemd-run
export MR_REMOTE_USER=jobs                      # непривилегированный пользователь задач
# по желанию: MR_REMOTE_ROOT (по умолчанию /home/$MR_REMOTE_USER/mr-jobs), MR_REMOTE_SSH,
#             MR_REMOTE_UNIT (префикс имён юнитов, по умолчанию mr-)
```

Задача идёт с nice 15 и idle-приоритетом ввода-вывода; `--cpus` и `--mem` ограничивают её
дальше — на общей машине это стоит делать.

```bash
remote/setup-box.sh --rust --lean          # один раз: uv, Rust и elan для пользователя задач

remote/mr-remote.sh submit --name colours84 --cpus 0-2 --mem 12G -- \
  'source remote/py-env.sh && cd metalibrary && python colour_solver.py data/sseq_S3_p3_150.csv 84 --out "$JOB_OUT"'
remote/mr-remote.sh status               # все задачи: RUNNING / DONE / FAILED (exit N) / LOST
remote/mr-remote.sh status ID            # одна задача и хвост её лога
remote/mr-remote.sh log ID 100
remote/mr-remote.sh fetch ID             # out/, log, meta, exit → remote-results/ID/
remote/mr-remote.sh cancel ID
```

- Уезжают все файлы, которые отслеживает git, **с незакоммиченными правками**. Файл вне индекса
  не уезжает: скрипт называет такие файлы до отправки; `git add` их или передай `--untracked`.
- В `meta` записываются коммит и то, было ли дерево грязным: результат всегда можно сопоставить
  с кодом, который его посчитал.
- На машине у каждой задачи свой `$MR_REMOTE_ROOT/<ID>/`: `tree/` (присланные файлы, задача
  работает в них), `out/` (`$JOB_OUT`, его забирает `fetch`), `log` (stdout и stderr; в начале —
  ядра, на которых она реально идёт), `cmd.sh` и `meta`, в конце — `exit`. Задача — временный
  юнит systemd `mr-<ID>`; `systemctl status mr-<ID>` на машине показывает его как есть.
- Задаче видны `$JOB_OUT`, `$JOB_ROOT` и `$JOB_CACHE` (общий между задачами: `uv`, venv по хешу
  `requirements-py.txt`, `target/` Rust). `TMPDIR` — `$JOB_ROOT/tmp`.
- Python: `source remote/py-env.sh` (venv делает `uv`, так что хватает системного `python3`
  без `ensurepip`; в систему ничего не ставится).
- Коды выхода: `0` — всё хорошо; `1` — задача упала или (у `fetch`) ещё не кончилась; `2` —
  ничего не запускалось (нет связи, плохие аргументы, отправка не удалась). «Задача упала» и
  «задача не запускалась» — разные ответы, и скрипт их не смешивает.
