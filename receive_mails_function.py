import os
import logging
import jsonpickle
import base64
from bs4 import BeautifulSoup
import quotequail
import mailparser

import jsonpickle

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def parse_mail(event, context):
    logger.info("## EVENT\r" + jsonpickle.encode(event))
    logger.info("## CONTEXT\r" + jsonpickle.encode(context))

    ses_message = jsonpickle.decode(event["Records"][0]["Sns"]["Message"])
    b64_msg = base64.b64decode(ses_message["content"])

    mail_parsed = mailparser.parse_from_bytes(b64_msg)
    mail = mail_parsed
    if len(mail.text_plain) > 0:
        mail = mail.text_plain[0]
    else:
        soup = BeautifulSoup(mail.text_html[0], features="html.parser")
        mail = soup.get_text()

    used_do_not_delete = False
    mail_unwrap = quotequail.unwrap(mail)
    if mail_unwrap and "text_top" in mail_unwrap:
        mail = mail_unwrap["text_top"]
    else:
        if (
            len(mail_parsed.text_html) > 0
            and "do_not_delete_this" in mail_parsed.text_html[0]
        ):
            used_do_not_delete = True
            mail = mail_parsed.text_html[0]
            newsoup = BeautifulSoup(
                mail[: mail.find("do_not_delete_this")], "html.parser"
            )
            for br in newsoup.find_all("br"):
                br.replace_with("\n")
            mail = newsoup.get_text()

    logger.info("## USED DELETE ID\r" + str(used_do_not_delete))
    logger.info("## MAIL\r" + mail)

    sender = mail_parsed.mail["from"][0][1]
    recipients = mail_parsed.mail["to"][0][1]
    # recipients = [e[1] for e in mail_parsed.mail['to']]
    # subject = mail_parsed.mail["subject"]

    # logger.info('## SES\r' + str(ses_message))
    logger.info("## SENDER\r" + sender)  # email.utils.parseaddr(
    logger.info("## RECEIVER\r" + recipients)

    return (
        mail,
        sender,
        recipients,
    )


def lambda_handler(event, context):
    mail, sender, recipients = parse_mail(event, context)
    ### save a json in the database using database.py
    return True
