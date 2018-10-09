#
# Copyright(c) 2018 Asit Dhal.
# Distributed under the MIT License (http://opensource.org/licenses/MIT)
#

from jira import JIRA
from config import *
import sys, re, optparse, os
import os.path

def slugify(value):    
    value = str(re.sub('[^\w\s-]', '', value).strip().lower())
    value = str(re.sub('[-\s]+', '-', value))
    return value

def sizeof_fmt(num, suffix='B'):
    for unit in ['','K','M','G','T','P','E','Z']:
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


options = { 'server': ENDPOINT }
jira = JIRA(options, basic_auth=(USERNAME, PASSWORD))


def fetch_jira_issue(issue_id, override_flag=True):
    issue = jira.issue(issue_id)
    summary = issue.fields.summary
    print ("feting {} : {}".format(issue_id, summary))
    issue_title = slugify(summary)
    download_dir_name = issue_id + '_' + issue_title

    download_path = os.path.join(DOWNLOAD_PATH, download_dir_name)

    if len(issue.fields.attachment) == 0:
        print ("{} has no attachments".format(issue_id))

    else:
        try:
            os.makedirs(download_path)

        except FileExistsError:
            if override_flag:
                print ("Issue already exists or the path is not empty")
            else:
                print ("Please empty the path or run with -f option")
                return

        for attachment in issue.fields.attachment:
            print("Downloading {filename} of size: {size}".format(filename=attachment.filename, size=sizeof_fmt(attachment.size)))
            issue_path = os.path.join(download_path, attachment.filename)
            f = open(issue_path, 'wb')
            f.write(attachment.get())
            f.close()



def main():
    parser = optparse.OptionParser()
    parser.add_option("-d", "--debug", dest="debug_flag", default=False, help="write report to FILE")
    parser.add_option("-i", "--issue", dest="issue_id", help="JIRA Issue Id")
    parser.add_option("-f", "--force", dest="force_flag", default=True, help="Override dirs/files")
    parser.add_option("-c", "--clean", dest="clean_flag", default=False, help="Delete closed Issues")
    (options, args) = parser.parse_args()

    fetch_jira_issue(options.issue_id, options.force_flag)


if __name__ == "__main__":
    main()
