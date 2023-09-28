import os
import glob
import re
import datetime
from collections import Counter
from jinja2 import Environment, FileSystemLoader
import gzip

# Define the log directory and output directory
log_dir = "/var/log/apache2/"
output_dir = "/tmp/stats/"

# Ensure the output directory exists
os.makedirs(output_dir, exist_ok=True)

# Define a list of possible date formats to try for access logs
access_date_formats = [
    '%d/%b/%Y:%H:%M:%S',
    '%a %b %d %H:%M:%S %Y',
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

# Function to consolidate stats and generate HTML report for the default logs
def generate_default_report(log_files, output_dir):
    default_stats = {
        'daily_access_counts': Counter(),
        'popular_pages': Counter(),
        'error_counts': Counter()
    }

    for log_file in log_files:
        with open(log_file, 'r', encoding='utf-8') as log:
            if log_file.endswith('.gz'):
                log = gzip.open(log_file, 'rt')

            for line in log:
                date_obj = parse_date(line, access_date_formats)

                if date_obj:
                    default_stats['daily_access_counts'][date_obj.date()] += 1

                if "error" in log_file:
                    error_date_obj = parse_date(line, [error_date_format])
                    if error_date_obj:
                        error_message = line.split('] ')[-1].strip()
                        default_stats['error_counts'][(error_date_obj, error_message)] += 1

                page_match = re.search(r'"GET (.*?) HTTP', line)
                if page_match:
                    page = page_match.group(1)
                    default_stats['popular_pages'][page] += 1

    # Create HTML/CSS report for the default logs
    env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))
    template = env.get_template('report_template.html')
    output_html = os.path.join(output_dir, 'default.html')
    with open(output_html, 'w') as html_file:
        html_file.write(template.render(
            domain='Default Logs',
            daily_access=default_stats['daily_access_counts'],
            popular_pages=default_stats['popular_pages'].most_common(10),
            top_errors=default_stats['error_counts'].most_common(10)
        ))

    return output_html

# Process all log files in the log directory
log_files = glob.glob(os.path.join(log_dir, '*.log*'))
log_files.extend(glob.glob(os.path.join(log_dir, '*.log.*')))
log_files.extend(glob.glob(os.path.join(log_dir, 'other_vhosts_access.log*')))
log_files.extend(glob.glob(os.path.join(log_dir, 'other_vhosts_access.log.*')))

# Filter out log files that are not default Apache logs
default_log_files = [log_file for log_file in log_files if not re.search(r'_access|_error', log_file)]

# Generate the HTML report for default logs
generate_default_report(default_log_files, output_dir)

# Dictionary to store statistics for each domain
domain_stats = {}

for log_file in log_files:
    domain = os.path.basename(log_file).split('_')[0]

    if domain not in domain_stats:
        domain_stats[domain] = {
            'daily_access_counts': Counter(),
            'popular_pages': Counter(),
            'error_counts': Counter()
        }

    date_access_counts, page_counts, error_count = generate_domain_report([log_file], output_dir)
    domain_stats[domain]['daily_access_counts'].update(date_access_counts)
    domain_stats[domain]['popular_pages'].update(page_counts)
    domain_stats[domain]['error_counts'].update(error_count)

# Create HTML/CSS report for each domain
for domain, stats in domain_stats.items():
    output_html = os.path.join(output_dir, f'{domain}.html')
    with open(output_html, 'w') as html_file:
        html_file.write(template.render(
            domain=domain,
            daily_access=stats['daily_access_counts'],
            popular_pages=stats['popular_pages'].most_common(10),
            top_errors=stats['error_counts'].most_common(10)
        ))

print(f"Statistics generated and saved in {output_dir}")
