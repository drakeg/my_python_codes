import os
import glob
import re
import datetime
from collections import Counter
from jinja2 import Environment, FileSystemLoader
import gzip
import chardet

# Define the log directory and output directory
log_dir = "/var/log/apache2/"
output_dir = "/tmp/stats/"

# Ensure the output directory exists
os.makedirs(output_dir, exist_ok=True)

# Define a list of possible date formats to try for access logs
access_date_formats = [
    '%d/%b/%Y:%H:%M:%S %z',
    # Add more formats as needed
]

# Define the date format for error logs
error_date_format = '%a %b %d %H:%M:%S.%f %Y'

# Function to parse the date from a log line
def parse_date(line, date_formats):
    for format_str in date_formats:
        try:
            date_match = re.search(r'\[({})\]'.format(format_str), line)
            if date_match:
                date_str = date_match.group(1)
                date_obj = datetime.datetime.strptime(date_str, format_str)
                return date_obj
        except ValueError:
            pass
    return None

# Function to detect the encoding of a file
def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        detector = chardet.universaldetector.UniversalDetector()
        for line in file:
            detector.feed(line)
            if detector.done:
                break
        detector.close()
        encoding = detector.result['encoding']
    return encoding

# Function to consolidate stats and generate HTML report for a domain
def generate_domain_report(domain, log_files, output_dir):
    domain_stats = {
        'daily_access_counts': Counter(),
        'popular_pages': Counter(),
        'error_counts': Counter()
    }

    for log_file in log_files:
        encoding = detect_encoding(log_file)
        with open(log_file, 'r', encoding=encoding) as log:
            if log_file.endswith('.gz'):
                log = gzip.open(log_file, 'rt')

            for line in log:
                date_obj = parse_date(line, access_date_formats)

                if date_obj:
                    domain_stats['daily_access_counts'][date_obj.date()] += 1

                if "error" in log_file:
                    error_date_obj = parse_date(line, [error_date_format])
                    if error_date_obj:
                        error_message = line.split('] ')[-1].strip()
                        domain_stats['error_counts'][error_message] += 1

                page_match = re.search(r'"GET (.*?) HTTP', line)
                if page_match:
                    page = page_match.group(1)
                    domain_stats['popular_pages'][page] += 1

    # Create HTML/CSS report for the domain
    env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))
    template = env.get_template('report_template.html')
    output_html = os.path.join(output_dir, f'{domain}.html')
    with open(output_html, 'w') as html_file:
        html_file.write(template.render(
            domain=domain,
            daily_access=domain_stats['daily_access_counts'].items(),
            popular_pages=domain_stats['popular_pages'].most_common(10),
            top_errors=domain_stats['error_counts'].most_common(10)
        ))

    return output_html

# Function to get log files, including rotated and gzipped files
def get_log_files(log_dir, prefix):
    log_files = glob.glob(os.path.join(log_dir, f'{prefix}*.log*'))
    log_files.extend(glob.glob(os.path.join(log_dir, f'{prefix}*.log.*')))
    log_files.extend(glob.glob(os.path.join(log_dir, f'{prefix}*.gz')))
    return log_files

# Process all log files in the log directory
access_log_files = get_log_files(log_dir, 'access')
error_log_files = get_log_files(log_dir, 'error')

# Generate the HTML report for default logs (access.log and error.log)
default_report_html = generate_domain_report('default', access_log_files + error_log_files, output_dir)

# Process domain-specific log files
domain_logs = glob.glob(os.path.join(log_dir, '*_access.log*'))
domain_logs.extend(glob.glob(os.path.join(log_dir, '*_error.log*')))

# Extract unique domain names from the log file names
unique_domains = set()

for domain_log in domain_logs:
    domain_match = re.search(r'
