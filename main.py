#
# Copyright(c) 2018 Asit Dhal.
# Distributed under the MIT License (http://opensource.org/licenses/MIT)
#

import json
from jira import JIRA, JIRAError
import sys, re, os
import os.path
import argparse
import logging
import subprocess

unpack_path = None

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


def load_config():
    global unpack_path
    config = list()
    config_content = ""
    with open('config.json', 'r') as content_file:
        config_content = content_file.read()

    parsed_config = json.loads(config_content)
    tags = parsed_config.get("tags", None)
    unpack_path = parsed_config.get("7z-path", None)

    if not tags:
        logging.error("config.json has no tags section")
        return
    for tag in tags:
        if not isinstance(tag, dict):
            logging.error("tag should have a tag, username, password, endpoint and download_path")
            continue
        else:
            ret = False
            if not tag.get("username", None):
                logging.error("jira_link should have a username")
                ret = True
            if not tag.get("password", None):
                logging.error("jira_link should have a password")
                ret = True
            if not tag.get("endpoint", None):
                logging.error("jira_link should have an endpoint")
                ret = True
            if not tag.get("download_path", None):
                logging.error("jira_link should have download_path")
                ret = True
            if not tag.get("tag", None):
                logging.error("jira_link should have a tag")
                ret = True
            if ret:
                continue
            
            item = dict()
            item["username"] = tag["username"]
            item["password"] = tag["password"]
            item["endpoint"] = tag["endpoint"]
            item["download_path"] =tag["download_path"]
            item["name"] = tag["tag"]
            config.append(item)

    return config

class JiraRequester:
    def __init__(self, username, password, endpoint, download_path):
        self.username = username
        self.password = password
        self.endpoint = endpoint
        self.download_path = download_path

        options = {'server': self.endpoint}
        try:
            self.jira_instance = JIRA(options, basic_auth=(self.username, self.password), max_retries=1)
        except Exception as e:
            logging.critical("%s", e)
            sys.exit()

    def fetch_jira_issue(self, issue_id, override_flag=True):
        downloaded_files = list()
        try:
            issue = self.jira_instance.issue(issue_id)
            summary = issue.fields.summary
            logging.info("Fetching %s : %s", issue_id, summary)
            issue_title = slugify(summary)
            download_dir_name = issue_id + '_' + issue_title

            download_path = os.path.join(self.download_path, download_dir_name)

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
                    downloaded_files.append(issue_path)
        except JIRAError as e:
            logging.critical("%d: Error: %s", e.status_code, e.text)

        return downloaded_files
        


def clean():
    pass

def postprocess(file_list, unpack_tool):
    for f in file_list:
        _, ext = os.path.splitext(f)
        ext = ext[1:]
        if ext.lower() in ["7z", "zip"]:
            logging.info("Unpacking: %s", f)
            subprocess.call(unpack_tool, f)

def parse_argument(choices):
    parser = argparse.ArgumentParser(description='Jira attachment downloader')
    parser.add_argument("-d", "--debug", dest="debug_flag", default=False,
                        action="store_true", help="write report to FILE")
    parser.add_argument("-i", "--issue", dest="issue_id", help="JIRA Issue Id")
    parser.add_argument("-f", "--force", dest="force_flag", default=False,
                        action="store_true", help="Override dirs/files")
    parser.add_argument("-c", "--clean", dest="clean_flag", default=False,
                        action="store_true", help="Delete closed Issues")
    
    parser.add_argument("-t", "--tag", dest="tag", choices=choices,
                          default=choices[0], help="JIRA Tags")

    return parser.parse_args()


def main():
    config = load_config()
    parsed_args = parse_argument(choices=tuple([item["name"] for  item in config]))
    
    if parsed_args.debug_flag:
        logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(message)s', level=logging.INFO)

    logging.debug("args: %s", str(parsed_args))
    logging.debug("config: %s", json.dumps(config, indent=2, sort_keys=True))

    if not parsed_args.issue_id and not parsed_args.clean_flag:
        logging.warn("Either specify an issue id or clean flag")

    selected_index = [i for i,x in enumerate(config) if x["name"] == parsed_args.tag][0]
    jira_requester = JiraRequester(config[selected_index]["username"], config[selected_index]["password"], config[selected_index]["endpoint"], config[selected_index]["download_path"])
    if parsed_args.issue_id:
        file_list = jira_requester.fetch_jira_issue(parsed_args.issue_id, parsed_args.force_flag)
        postprocess(file_list, unpack_path)
    elif parsed_args.clean_flag:
        clean()


if __name__ == "__main__":
    main()
