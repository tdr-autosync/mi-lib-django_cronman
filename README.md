# django-cronman

## Overview

Django app to define and manage periodic tasks at Python level.

## Installation

`django-cronman` can be installed directly from PyPI using `pip`:

```bash
pip install django-cronman
```

You can also install it with additional dependencies to be able to use Cron Remote Manager.

```bash
pip install django-cronman[redis]
```

## Define a new cron job

Cron job definition is inspired by Django Admin configuration. To add a new job, you have to create `cron_job.py`
file inside an app, create `BaseCronJob` subclass inside and register it:

```python
from cronman.job import BaseCronJob, cron_job_registry

class HelloWorld(BaseCronJob):
    """Demo Cron Job class"""

    def run(self):
        """Main logic"""
        pass

cron_job_registry.register(HelloWorld)
```

Cron job classes are registered (and referred to) by name, which may be customized on registration:
```python
cron_job_registry.register(HelloWorld, name='Hello')
```
It's also possible to retrieve or unregister a class (e.g. while testing):
```python
cron_job_registry.get('HelloWorld')
cron_job_registry.unregister('HelloWorld')
```
If there is more than 1 cron job in given app, it's recommended to create a package instead of single `cron_jobs` module, create one submodule per class and do the imports and registration in package's  `__init__.py`.

## Configure cron jobs

To ensure that a cron job is executed periodically, you have add an entry to `CRON_JOBS`:

```python
CRON_JOBS = (
    ...
    # (<time spec>, <job spec>)
    # 'HelloWorld' will be executed a 5:15AM every day:
    ('   15   5   *   *   *', 'HelloWorld'),
)
```

Set ```CRONMAN_JOBS_MODULE``` to the dotted path name of the module where cron jobs are specified. Remember, this module MUST have a ```CRON_JOBS``` attribute. ```CRONMAN_JOBS_MODULE``` is ```None``` by default. For example:

```python
# settings_local.py

CRONMAN_JOBS_MODULE = 'app.cron_jobs.name'
```

## Run the scheduler

Cron jobs defined in ```settings.CRONMAN_JOBS_MODULE``` are started by `cron_scheduler` command from `cron` app.
This command constructs a list of jobs that should be executed in current period (now +/- 1 minute)
and creates **a new subprocess** for each job.
```
python manage.py cron_scheduler run
```
This command should be added to system's crontab on server responsible for running periodic tasks
and executed every 2 minutes.

## Run single cron job

Command `cron_worker run <job spec>` is responsible for executing cron jobs:
```
python manage.py cron_worker run HelloWorld
```

## Cron job parameters

Cron job classes can accept parameters which are passed to `run` method as positional or named arguments:
```python
class HelloWorld(BaseCronJob):
    """Demo Cron Job class"""

    def run(self, what, sleep=None):
        """Main logic"""
        print "Hello {}".format(what)
        if sleep:
            time.sleep(int(sleep))
    ...
```
```
python manage.py cron_worker run HelloWorld:world,sleep=5
```
Parameters are passed as string values, any type casts should be made in `run` method.
Quoted string with spaces are supported, but comma can be used only as argument separator:
```
python manage.py cron_worker run HelloWorld:"big world",sleep=5
```
There are utility functions for extracting lists and boolean values in `cronman.utils` module.

## Configure Cronitor support

`cron_worker` command can notify Cronitor when a job is started, finished or it has failed.
To enable this you have to:
1. Enable Cronitor support in settings `CRONMAN_CRONITOR_ENABLED = True`
2. Configure you cron job class:
```python
class HelloWorld(BaseCronJob):
    """Demo Cron Job class"""
    cronitor_id = 'ab12z'  # ID is assigned in Cronitor's dashboard
```

We may disable sending optional "RUN" and "FAIL" pings to Cronitor when cron job starts by setting `cronitor_ping_run = False` or `cronitor_ping_fail = False` but this doesn't seem to be necessary.

**Important note:**
When adding a new monitor in Cronitor dashboard, please use type **heartbeat**. Avoid using **cron job** monitors, as they're sending false-positive alerts "Has not run on schedule".


## Configure lock

Tasks can acquire locks to prevent concurrent calls. Locks have form of PIDfiles located in `settings.CRONMAN_DATA_DIR`. To modify lock behavior for given cron job class you can set `lock_type` attribute:

```python
from cronman.taxonomies import LockType

class HelloWorld(BaseCronJob):
    """Demo Cron Job class"""
    lock_type = LockType.PARAMS
```
The following values are supported:
* `None` - no lock, concurrency is allowed
* `LockType.CLASS` (default) - only one instance of given cron job class can be run at the same time (e.g. `Foo:p=1` and `Foo:p=2` can't work concurrently)
* `LockType.PARAMS` - only one combination of class and params can be run at the same time (e.g. `Foo:p=1` and `Foo:p=2` can work concurrently, but another call to `Foo:p=1` will be prohibited)
Locks acquired/released by `cron_worker` command.

We can configure a shared lock for several cron job classes to make sure only one of them is running:

```python
from cronman.taxonomies import LockType

class HelloWorld1(BaseCronJob):
    """Demo Cron Job class (1)"""
    lock_type = LockType.CLASS
    lock_name = 'HelloWorld'

class HelloWorld2(BaseCronJob):
    """Demo Cron Job class (2)"""
    lock_type = LockType.CLASS
    lock_name = 'HelloWorld'
```

## Configure CPU and IO priority

We can assign CPU priority (`nice`) to a cron job class by using `worker_cpu_priority` attribute:
```python
from cronman.taxonomies import CPUPriority

class NiceHellowWorld(BaseCronJob):
    """Hello World running through `nice -n 19`"""
    worker_cpu_priority = CPUPriority.LOWEST
```
We can also customize IO priority (`ionice`) by assigning one of values from `cronman.taxonomies.IOPriority` to `worker_io_priority` attribute, but this is not necessary in most cases, as `nice` changes IO priority as well.

Commands `cron_scheduler run`, `cron_worker resume`, and cron job `RunCronTasks` will spawn worker processes with respect to CPU and IO priorities assigned to cron job classes. These settings **are not** enforced when running `cron_worker run` so you have to prepend `nice`/`ionice` to such calls manually.

## List and kill running cron jobs

Command `cron_worker status` shows currently running cron jobs - PIDfile name, PID and status (`ALIVE`, `DEAD`).
Search results can be limited by `job spec` (cron job name, parameters):
```
python manage.py cron_worker status
python manage.py cron_worker status Foo
python manage.py cron_worker status Foo:bar=1
```

Command `cron_worker kill` kills active cron jobs, gracefully (`SIGTERM`) or by force when process refuses to die (`SIGKILL`). List of tasks can be limited by `job spec`:
```
python manage.py cron_worker kill
python manage.py cron_worker kill Foo
python manage.py cron_worker kill Foo:bar=1
```
Single process can be killed also using PID:
```
python manage.py cron_worker kill 39078
```

## Resuming cron jobs

Subset of cron jobs can be resumed after being killed:

```python

class ResumableHelloWorld(BaseCronJob):
    """Demo Cron Job class"""
    can_resume = True
```

Command `cron_worker resume` starts all killed cron jobs with `can_resume` capability:
```
python manage.py cron_worker resume
```

To remove all entries about dead cron jobs and make sure they won't be resumed we can run `cron_worker clean` command:
```
python manage.py cron_worker clean
```

Command `cron_worker suspend` cleans all previous entries about dead cron jobs and then kills all running ones to make sure that next `resume` will raise only recently killed jobs:
```
python manage.py cron_worker suspend
```


## List available cron jobs

Command `cron_worker info` shows list of all available cron jobs:
```
python manage.py cron_worker info
```
When cron job name is passed to this command, system displays docstring and parameters of given cron job:
```
python manage.py cron_worker info Foo
```

## Disable the scheduler

Scheduler command can be disabled temporarily:
```
python manage.py cron_scheduler disable
```
and re-enabled later:
```
python manage.py cron_scheduler enable
```
Calls to `cron_scheduler run` will not spawn worker processes while scheduler is disabled.

## Send errors to sentry

Errors in cron job classes are intercepted by `cron_worker` and sent to Sentry using the same config as other Django commands (`settings.RAVEN_MANAGEMENT_COMMAND_CONFIG`).
If `settings.CRONMAN_RAVEN_CMD` is defined, the scheduler will use it as execution script for worker processes, e.g.
`python manage.py cron_worker run Foo:bar=1` will be converted to `{CRONMAN_RAVEN_CMD} -c "python manage.py cron_worker run Foo:bar=1"`

## Cron Tasks - running cron jobs from Admin area

Some cron jobs can be requested to start from Admin area: **Admin > Cron > Cron Tasks**
To add a cron job class to the list in Admin we need to set `ALLOWED_CRON_TASKS` setting:

```python

ALLOWED_CRON_TASKS = (
    'HelloWorld',
)
```
To request another run of given cron job we can just create a new `CronTask` record in Admin.
Cron job `RunCronTasks` started every 4 minutes by the scheduler will spawn a separate worker process for each pending Cron Task.

## Changelog

2019-04-30 - 1.1.1 Pre-commit.com hooks support. Docs update
2019-03-13 - 1.1.0 Add support for cronitor ping for cron_scheduler
2019-02-25 - 1.0.0 Initial version released
