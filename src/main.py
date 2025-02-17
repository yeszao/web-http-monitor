import requests
import logging
import smtplib
from email.mime.text import MIMEText
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from apscheduler.schedulers.background import BackgroundScheduler

from src.config import  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, \
    MONITORED_URLS, ALERT_TO_EMAIL, CHECK_TIMEOUT, CHECK_INTERVAL
from src.log import initialize_logging


def send_alert(receiver, body):
    msg = MIMEText(body)

    msg['Subject'] = "Website Monitor Alert"
    msg['From'] = SMTP_USER
    msg['To'] = receiver
    
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")


def check_url(url):
    headers = {"User-Agent": "Askis-bot"}
    try:
        response = requests.get(url, headers=headers, timeout=CHECK_TIMEOUT)
        if response.status_code != 200:
            error = f"Error! Url [{url}] was down!!! Return status code is [{response.status_code}]."
            logging.error(f"URL [{url}] return failed!")
            return error
        else:
            logging.info(f"URL [{url}] return OK!")
            return None
    except Exception as e:
        error = f"Error! Url [{url}] failed with exception: {str(e)}"
        logging.error(f"URL [{url}] failed with exception: {str(e)}")
        return error

def check_urls():
    errors = []
    with ThreadPoolExecutor() as executor:
        future_to_url = {executor.submit(check_url, url): url for url in MONITORED_URLS}
        for future in as_completed(future_to_url):
            error = future.result()
            if error:
                errors.append(error)

    if errors:
        body = '\n'.join(errors)
        send_alert(ALERT_TO_EMAIL, body)


if __name__ == '__main__':
    initialize_logging("app.log")

    scheduler = BackgroundScheduler()
    scheduler.add_job(check_urls, 'interval', seconds=CHECK_INTERVAL)
    scheduler.start()
    
    # Run immediately on startup
    check_urls()
    
    logging.info("Monitor started. Will run every 5 minutes.")
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info("Monitor stopped.")
