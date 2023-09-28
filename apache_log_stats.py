import os
import glob
import re
import datetime
from collections import Counter
import matplotlib.pyplot as plt
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

# Function to consolidate stats and generate HTML report for a domain
def generate_domain_report(domain, output_dir):
    domain_stats = {
        'daily_access_counts': Counter(),
        'popular_pages': Counter(),
        'error_counts': Counter()
    }

    # Process all log files for the current domain
    log_files = glob.glob(os.path.join(log_dir, f'{domain}_access*.log*')) + \
                glob.glob(os.path.join(log_dir, f'{domain}_error*.log*'))

    for log_file in log_files:
        with open(log_file, 'r', encoding='utf-8') as log:
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
                        domain_stats['error_counts'][(error_date_obj, error_message)] += 1

                page_match = re.search(r'"GET (.*?) HTTP', line)
                if page_match:
                    page = page_match.group(1)
                    domain_stats['popular_pages'][page] += 1

    # Create HTML/CSS report for the domain
    env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))
    template = env.get_template('report_template.html')
    output_html = os.path.join(output_dir, f'{domain}_stats.html')
    with open(output_html, 'w') as html_file:
        html_file.write(template.render(
            domain=domain,
            daily_access=domain_stats['daily_access_counts'],
            popular_pages=domain_stats['popular_pages'].most_common(10),
            top_errors=domain_stats['error_counts'].most_common(10)
        ))

    return output_html

# Process all domains and generate an index.html file
domains = set()
for log_file in glob.glob(os.path.join(log_dir, '*.log*')):
    domain = os.path.basename(log_file).split('_')[0]
    domains.add(domain)

index_html_content = '<html><body><h1>Apache Log Statistics</h1><ul>'

for domain in domains:
    report_file = generate_domain_report(domain, output_dir)
    index_html_content += f'<li><a href="{os.path.basename(report_file)}">{domain} Statistics</a></li>'

index_html_content += '</ul></body></html>'
index_html_path = os.path.join(output_dir, 'index.html')
with open(index_html_path, 'w') as index_file:
    index_file.write(index_html_content)

print(f"Statistics generated and saved in {output_dir}")
