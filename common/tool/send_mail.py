from init.settings import conf_dict, user_logger, error_logger
import smtplib
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.header import Header
import os
import email.encoders
from common.tool.type_tool import TypeTool
import time
import traceback
from common.tool.common_func import get_sub_string
import re


def send_mail(email_list, subject, email_text, filepath="", sub_type="text", email_sender=""):
    try:
        # 发送email
        user_logger.debug("email1")
        receiver = list(set(get_email_list(email_list).split(';')))
        user_logger.debug(conf_dict)
        if email_sender == "REPORT":
            sender = conf_dict["EMAIL-REPORT"]["sender"]
            smtpserver = conf_dict["EMAIL-REPORT"]["smtpserver"]
            username = conf_dict["EMAIL-REPORT"]["username"]
            password = conf_dict["EMAIL-REPORT"]["password"]
        else:
            sender = conf_dict["EMAIL"]["sender"]
            smtpserver = conf_dict["EMAIL"]["smtpserver"]
            username = conf_dict["EMAIL"]["username"]
            password = conf_dict["EMAIL"]["password"]
            user_logger.debug("email2 %s" % receiver)

        # 三个参数：第一个为文本内容，第二个 plain 设置文本格式，第三个 utf-8 设置编码
        msg = MIMEMultipart()  #
        if sub_type == "text":
            text_msg = MIMEText(email_text, 'plain', 'utf-8')  # 文本格式
        elif sub_type == "html":
            text_msg = MIMEText(email_text, _subtype='html', _charset='utf-8')  # html格式
        else:
            text_msg = MIMEText(email_text, 'plain', 'utf-8')  # 文本格式
        msg.attach(text_msg)
        msg['From'] = sender
        msg['To'] = ";".join(receiver)
        msg['Subject'] = Header(subject, 'utf-8')
        # 构造MIMEBase对象做为文件附件内容并附加到根容器
        filepath = filepath.strip()
        if os.path.isfile(filepath):
            contype = 'application/octet-stream'
            maintype, subtype = contype.split('/', 1)
            data = open(filepath, 'rb')
            file_msg = MIMEBase(maintype, subtype)
            file_msg.set_payload(data.read())
            data.close()
            email.encoders.encode_base64(file_msg)
            filename_list = filepath.split('/')
            filename = filename_list[len(filename_list) - 1]
            basename = os.path.basename(filename)
            file_msg.add_header('Content-Disposition', 'attachment', filename=basename)
            msg.attach(file_msg)
        is_send_success = False
        resend_times = 0
        for i in range(0, 3):
            smtp = ""
            try:
                smtp = smtplib.SMTP(smtpserver)
                smtp.login(username, password)
                # 用smtp发送邮件
                smtp.sendmail(sender, receiver, msg.as_string())
                is_send_success = True
                break
            except Exception as e:
                resend_times += 1
                user_logger.debug("发送第%s次失败！2秒后重试！" % resend_times)
                error_logger.error("%s\n%s" % (traceback.format_exc(),
                                               ("email_address: %s" % email_list)
                                               if ("Invalid address" in str(traceback.format_exc()))
                                               else "")
                                   )
                time.sleep(2)  # 休眠10秒，10秒后重发
                if len(receiver) == 0:
                    return False
            finally:
                if smtp != "":
                    smtp.quit()
        if is_send_success:
            return True
        else:
            return False
    except Exception as e:
        print(traceback.format_exc())
        return False


def get_email_list_by_email_receivers(email_receivers):
    emaillist = email_receivers.split(",")
    retemail = ""
    for tmpemail in emaillist:
        if "(" in tmpemail and ")" in tmpemail:
            retemail += get_sub_string(tmpemail, "(", ")") + "@ke.com;"
        else:
            retemail += tmpemail + ";"
    return retemail


def get_email_list(emailstr):
    email_list = emailstr.replace(";", ",").replace("；", ",").replace("，", ",").split(",")
    receiver = []
    for tmpemail in email_list:
        tmpemail = tmpemail.strip()
        if TypeTool.is_email(tmpemail):
            receiver.append(tmpemail)
        elif "(" in tmpemail and ")" in tmpemail:
            receiver.append(get_sub_string(tmpemail, "(", ")")+"@ke.com")
        elif "<" in tmpemail and ">" in tmpemail:
            receiver.append(get_sub_string(tmpemail, "<", ">"))
    return ";".join(receiver)


if __name__ == "__main__":
    retstr = get_email_list("wangjiliang001@ke.com;wangjiliang@ke.com；王蕾(wanglei05);,wang@ke.com，")
    print(retstr)
    print(type(retstr))
