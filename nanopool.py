import os
import requests
import threading
import logging
from logging.handlers import TimedRotatingFileHandler
import smtplib

dirname = os.path.dirname(__file__)

server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login("gutsalyuk.taras@gmail.com", "borfyzoibjupyxlc")


TIMEOUT = 900.0 # delay in seconds(900sec = 15min)
MINERASSISTANT = "http://127.0.0.1:8000/nanopool/"
NANOPOOLURL = "https://api.nanopool.org/v1/eth/user/"


# LOGGER
log_dir = os.path.join(dirname, 'logs')
if not os.path.exists(log_dir):
    os.mkdir(log_dir)
LOG_NAME = log_dir + '/' + 'nano.log'
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
log_handler = TimedRotatingFileHandler(LOG_NAME, when="midnight", backupCount=2)
log_handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(log_handler)
# --------------------------------------------

def main_loop():
    global task
    task = threading.Timer(TIMEOUT, main_loop)
    task.start()
    main()


def main():
    if is_server_responding(MINERASSISTANT):
        pools = requests.get(MINERASSISTANT + "get_pools/")
        check_reply_status(pools, pools_handler)
    else:
        handle_error('No connection could be made with Miner Assistant Backend because the target machine actively refused it. Script terminated')


def pools_handler(reply):
    logger.debug("Got list of active pools from miner assistant")
    pools_array = reply.json()["data"]
    if pools_array:
        for pool in pools_array:
            check_pool(pool)
    else:
        logger.debug("No active pools to check")


def check_pool(pool_id):
    logger.debug("Pool ID: %(pool)s. Checking general pool information with NanoPool server" % {'pool':pool_id})

    if is_server_responding(NANOPOOLURL):
        reply = requests.get(NANOPOOLURL + pool_id)
        logger.debug('Recieved reply from Nanopool about pool: %(pool)s' % {'pool': pool_id})
        check_reply_status(reply, nanopool_handler)
    else:
        handle_error("NanoPool server is Down. Script terminated")



def nanopool_handler(reply):
    info = reply.json()

    if info["status"]:

        logger.debug("Nanopool reply status is True. Forwading data to miner assistant")

        if is_server_responding(MINERASSISTANT):
            post_data = requests.post(MINERASSISTANT + "save_pool_stats/", json=info)
            check_reply_status(post_data, lambda *args: None)
        else:
            handle_error('No connection could be made with Miner Assistant Backend because the target machine actively refused it. Script terminated')
    else:
        logger.warning("Nanopool reply status is False. Data not sent to miner assistant")



def check_reply_status(reply, handler):
    if reply.status_code == 200:
        handler(reply)
    elif reply.status_code in  [500, 502, 503, 504]:
        handle_error('%(peer_name)s backend responded with server error. Script terminated.' % {'peer_name': reply.raw._pool.host})
    else:
        logger.warning("%(peer_name)s backend didn't respond with 200 status" % {'peer_name': reply.raw._pool.host})



def is_server_responding(url):
    try:
        respond = requests.get(url)
        return True
    except:
        return False


def handle_error(err_msg):
    logger.error(err_msg)
    task.cancel()

    SUBJECT = 'NanoPool Script Notification'
    TEXT = "Script terminated. Due to error: " + err_msg
    message = 'Subject: {}\n\n{}'.format(SUBJECT, TEXT)
    server.sendmail("gutsalyuk.taras@gmail.com", "gutsalyuk.taras@icloud.com", message)
    server.quit()

if __name__ == "__main__":
    main_loop()