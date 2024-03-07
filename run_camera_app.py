from CameraSurveillance import CameraSurveillance
from multiprocessing import Process
from time import sleep
import logging
from datetime import datetime
import signal
killsignal = False

def endall(*args):
    logging.info("[run_camera_app] signal trapped end all")
    global killsignal
    killsignal = True

def startCamera():
    camera_surveillance = CameraSurveillance()
    camera_surveillance.start()
def checkProcesses(proc_ref):
    global killsignal
    while(killsignal == False):
        if(proc_ref['proc'] == None):
            logging.info("[run_camera_app] proc=None |Detected Process is not running... starting up.")
            proc_ref['proc'] = Process(target=startCamera())
            proc_ref['proc'].start()
        else:
            if(proc_ref['proc'].is_alive()):
                sleep(10)
            else:
                logging.info("[run_camera_app] proc=Not Alive |Detected Process is not running... starting up.")
                proc_ref['proc'] = Process(target=startCamera())
                proc_ref['proc'].start()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, endall)
    curr_date = datetime.now().strftime("%Y%m%d")
    logging.basicConfig(format='%(asctime)s|%(levelname)s|%(message)s', filename=f"camera_surveillance_{curr_date}.log",filemode='a', level=logging.INFO)
    proc_ref = {'proc': None}
    checkProcesses(proc_ref)

