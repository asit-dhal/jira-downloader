#
# Copyright(c) 2018 Asit Dhal.
# Distributed under the MIT License (http://opensource.org/licenses/MIT)
#
import toml
from jira import JIRA
from config import *
import sys, re, os
import os.path
import argparse
import logging

def slugify(value):
    value = str(re.sub('[^\w\s-]', '', value).strip().lower())
    value = str(re.sub('[-\s]+', '-', value))
    return value

def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')



options = {'server': ENDPOINT}
jira = JIRA(options, basic_auth=(USERNAME, PASSWORD))

def load_config():
    config = dict()
    parsed_toml = toml.load("config.toml")
    for tag, _ in parsed_toml.items():
        if isinstance(parsed_toml[tag], dict):
            config[tag] = dict()
            if parsed_toml[tag].get("username", None):
                config[tag]["username"] = parsed_toml[tag]["username"]
            if parsed_toml[tag].get("password", None):
                config[tag]["password"] = parsed_toml[tag]["password"]
            if parsed_toml[tag].get("endpoint", None):
                config[tag]["endpoint"] = parsed_toml[tag]["endpoint"]
            config[tag]["download_path"] = parsed_toml[tag].get("download_path", "")

    return config



def fetch_jira_issue(issue_id, override_flag=True):
    issue = jira.issue(issue_id)
    summary = issue.fields.summary
    logging.info("Fetching %s : %s", issue_id, summary)
    issue_title = slugify(summary)
    download_dir_name = issue_id + '_' + issue_title

    download_path = os.path.join(DOWNLOAD_PATH, download_dir_name)

    if len(issue.fields.attachment) == 0:
        logging.info("%s has no attachments", issue_id)
    else:
        try:
            os.makedirs(download_path)

        except FileExistsError:
            if override_flag:
                logging.warning("Issue already exists or the path is not empty")
            else:
                logging.error("Please empty the path or run with -f option")
                return

        for attachment in issue.fields.attachment:
            logging.info("Downloading %s of size: %s", attachment.filename, sizeof_fmt(attachment.size))
            issue_path = os.path.join(download_path, attachment.filename)
            f = open(issue_path, 'wb')
            f.write(attachment.get())
            f.close()


def clean():
    pass

def postprocessing():
    pass


def main():
    config = load_config()

    parser = argparse.ArgumentParser(description='Jira attachment downloader')
    parser.add_argument("-d", "--debug", dest="debug_flag", default=False,
                        action="store_true", help="write report to FILE")
    parser.add_argument("-i", "--issue", dest="issue_id", help="JIRA Issue Id")
    parser.add_argument("-f", "--force", dest="force_flag", default=False,
                        action="store_true", help="Override dirs/files")
    parser.add_argument("-c", "--clean", dest="clean_flag", default=False,
                        action="store_true", help="Delete closed Issues")
    if len(config) > 1:
        parser.add_argument("-t", "--tag", dest="tag",
                          default=list(config.keys())[0], help="JIRA Tags")

    parsed_args = parser.parse_args()

    if parsed_args.debug_flag:
        logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(message)s', level=logging.INFO)

    if not parsed_args.issue_id and not parsed_args.clean_flag:
        logging.warn("Either specify an issue id or clean flag")

    if parsed_args.issue_id:
        fetch_jira_issue(parsed_args.issue_id, parsed_args.force_flag)
    elif parsed_args.clean_flag:
        clean()


if __name__ == "__main__":
    main()
