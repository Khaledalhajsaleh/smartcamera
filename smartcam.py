#!/usr/bin/env python3

# Main process for smartcam devices

# NOTE:
# This process is managed through systemd and is configured to auto-restart
# in the event of a graceful exit or failure. Please be careful when including
# code before the update procedures to avoid potentially breaking the
# ability to upgrade/repair these modules remotely.

import hashlib
import importlib
import logging
import multiprocessing as mp
import os
import py_compile
import shutil
import socket
import subprocess
import sys
import time

import git

################################################################################

repo = git.Repo('.')

logger = logging.getLogger()
logger.addHandler(logging.StreamHandler(sys.stdout))
if str(repo.active_branch) is 'release':
    logger.setLevel(logging.INFO)
else: # master/devrelease/others
    logger.setLevel(logging.DEBUG)

################################################################################

def check_pyfile_integrity(filename):
    try:
        py_compile.compile(filename, doraise=True)
    except Exception as e:
        logger.error(e)
        return(False)
    return(True)

def get_file_checksum(filename):
    if not os.path.isfile(filename):
        logger.error("File %s not found" % filename)
        return(None)

    with open(filename) as fileh:
        content = fileh.read().encode('utf-8')
        md5hash = hashlib.md5(content).hexdigest()
    return(md5hash)

def git_fetch_from_remote():
    fetch = repo.remotes.origin.fetch()[0]
    if fetch.old_commit is not None:
        logger.info("Fetching %.7s .. %.7s" % (fetch.old_commit, fetch.commit))
        return(True)
    return(False)

def git_merge_changes():
    merge_res = str(subprocess.check_output(['git', 'merge']))
    logger.debug(merge_res)
    #if "Already up to date" in merge_res:
    #    this-shouldnt-happen-so-cleanup
    return

def check_main_update():
    upgrade_md5 = get_file_checksum('smartcam.py')
    running_md5 = get_file_checksum('smartcam')

    if not running_md5: return(False) # development

    if upgrade_md5 != running_md5:
        logger.info('Update to main process detected')
        if check_pyfile_integrity('smartcam.py'):
            logger.debug('Main process update passed integrity tests')
            shutil.copyfile('smartcam.py', 'smartcam')
            return(True)
        else:
            logger.error('Main process update failed integrity tests')
    return(False)

def check_worker_update(initial_md5):
    current_md5 = get_file_checksum('worker.py')
    if initial_md5 != current_md5:
        logger.info('Update to worker process detected')
        return(True)
    return(False)


################################################################################

# initial worker process data:
try:
    worker_md5 = get_file_checksum('worker.py')

    import worker
    worker_p = mp.Process(target=worker.run, args=(logger,))
except Exception as e:
    worker_p = None
    logger.error(e)

###

while True:
    # check for updates:
    if git_fetch_from_remote():
        git_merge_changes()

        if check_main_update():
            logger.info('Main update installed, restarting daemon')
            sys.exit(0)

        if check_worker_update(worker_md5):
            if worker_p.is_alive():
                worker_p.terminate()
            try:
                importlib.reload(worker)
                logger.info('Worker updated, terminating existing worker')
            except Exception as e:
                logger.error(e)

    # monitor worker health:
    try:
        if worker_p.is_alive():
            logger.debug('Worker process seems alive and running')
        else:
            if worker_p.exitcode: # crashed
                logger.warning('Worker process seems to have crashed')
                worker_p = mp.Process(target=worker.run, args=(logger,))
            worker_p.start()
    except Exception as e:
        logger.error("Unable to initialise worker (%s)" % e)
    finally:
        time.sleep(60)