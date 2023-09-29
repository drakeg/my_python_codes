import os
import glob
import re
import datetime
from collections import Counter, defaultdict
from jinja2 import Environment, FileSystemLoader
import gzip
import chardet

# Define the log directory and output directory
log_dir = "/var/log/apache2/"
output_dir = "/tmp/stats/"

# Ensure the output directory exists
os.makedirs(output_dir, exist_ok=True)

# Function to detect the file encoding
def detect_encoding(file_path):
    try:
        with open(file_path, 'rb') as file:
            data = file.read(1024)
        encoding = chardet.detect(data)['encoding']
        return encoding
    except Exception as e:
        print(f"Error detecting encoding: {str(e)}")
        return 'utf-8'

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
def generate_domain_report(domain, log_files, output_dir):
    domain_stats = {
        'daily_access_counts': Counter(),
        'hourly_access_counts': defaultdict(Counter),  # New defaultdict for hourly counts by day
        'popular_pages': Counter(),
        'error_counts': Counter()
    }

    # Define a regular expression pattern to match the date within square brackets
    date_pattern = r'\[([^]]+)\]'

    for log_file in log_files:
        encoding = detect_encoding(log_file)
        with open(log_file, 'r', encoding=encoding) as log:
            if log_file.endswith('.gz'):
                log = gzip.open(log_file, 'rt')

            for line in log:
                # Find the date substring within square brackets
                date_match = re.search(date_pattern, line)
                if date_match:
                    date_str = date_match.group(1)
                    
                    # Define the date format
                    date_format = '%d/%b/%Y:%H:%M:%S %z'
                    
                    try:
                        # Parse the date string
                        date_obj = datetime.datetime.strptime(date_str, date_format)
                        
                        # Update daily_access_counts using the date part only
                        domain_stats['daily_access_counts'][date_obj.date()] += 1
                        
                        # Update hourly_access_counts using the day and hour parts of the date
                        domain_stats['hourly_access_counts'][date_obj.date()][date_obj.hour] += 1

                        if "error" in log_file:
                            error_date_obj = parse_date(line, [error_date_format])
                            if error_date_obj:
                                error_message = line.split('] ')[-1].strip()
                                domain_stats['error_counts'][(error_date_obj, error_message)] += 1

                        page_match = re.search(r'"GET (.*?) HTTP', line)
                        if page_match:
                            page = page_match.group(1)
                            domain_stats['popular_pages'][page] += 1
                    except ValueError:
                        pass

    # Create HTML/CSS report for the domain
    env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))
    template = env.get_template('report_template.html')
    output_html = os.path.join(output_dir, f'{domain}.html')
    with open(output_html, 'w') as html_file:
        html_file.write(template.render(
            domain=domain,
            daily_access=domain_stats['daily_access_counts'].items(),
            hourly_access=domain_stats['hourly_access_counts'].items(),  # Include hourly counts by day
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

# Define a list of possible date formats to try for access logs
access_date_formats = [
    '%d/%b/%Y:%H:%M:%S %z',
    '%a %b %d %H:%M:%S %Y',
    # Add more formats as needed
]

# Define the date format for error logs
error_date_format = '%a %b %d %H:%M:%S.%f %Y'

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
    domain_match = re.search(r'([a-zA-Z0-9.-]+)_', os.path.basename(domain_log))
    if domain_match:
        unique_domains.add(domain_match.group(1))

for domain in unique_domains:
    domain_specific_logs = [log_file for log_file in domain_logs if re.search(rf'{domain}_[\w.-]+', log_file)]
    generate_domain_report(domain, domain_specific_logs, output_dir)

print(f"Statistics generated and saved in {output_dir}")
