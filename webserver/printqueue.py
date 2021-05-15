import re
import socket
import subprocess
import time
from threading import Thread

from printjobs import JobStatus


class Printerthread(Thread):
    def __init__(self, config, logger):
        super().__init__()
        # make this a daemon thread
        self.daemon = True
        self.__queue = []
        self.__config = config
        self.__logger = logger

    def run(self):
        # main printing loop
        while True:
            # wait a few seconds if the queue is empty
            if len(self.__queue) == 0:
                time.sleep(self.__config['check_for_new_job_interval'])
            else:
                self.handle_print_job()

    def handle_print_job(self):
        printjob = self.get_first_job()
        self.__logger.info("Print job recieved from user %s with %d pages.", printjob.username, printjob.numpages)

        # dispatch print job
        # get cups server hostname
        hostname = socket.gethostbyname('cups')
        # call lp
        from_stdout = str(subprocess.check_output('lp -h ' + hostname + ':631 -d ABH ' + printjob.pdfpath,
                                                  shell=True))
        # extract the real printjob id
        jobid = re.search('(ABH-)([0-9]+)', from_stdout).group(2)
        # update the printjobs jobid
        printjob.jobid = jobid

        check_status = True

        while check_status:
            # sleep some time so we don't dos our own cups server
            time.sleep(float(self.__config['status_fetch_sleep_interval']))

            # fetch job status
            status = printjob.fetch_status()

            # break if job is completed or failed
            if status is JobStatus.COMPLETED or status is JobStatus.FAILED:
                check_status = False
            elif status is JobStatus.UNKNOWN:
                self.__logger.error('Received unknown status code')

        # TODO: do smb share processing and other important stuff here

    def enqueue(self, printjob):
        self.__queue.append(printjob)

    def get_first_job(self):
        return self.__queue.pop(0)