import boto3
import csv

def search_services(client, keyword):
    """Search for a specific service based on a keyword."""
    services = fetch_all_data(client.list_services)
    matching_services = [s for s in services if keyword.lower() in s['ServiceName'].lower()]
    
    for service in matching_services:
        print(f"Service Name: {service['ServiceName']}  Service Code: {service['ServiceCode']}")

def fetch_all_data(func, **kwargs):
    """Fetch all data from a paginated boto3 function."""
    results = []
    while True:
        response = func(**kwargs)
        results.extend(response['Quotas'])
        if 'NextToken' in response and response['NextToken']:
            kwargs['NextToken'] = response['NextToken']
        else:
            break
    return results


def save_to_csv(filename, headers, data):
    """Saves provided data to a CSV file."""
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        for row in data:
            writer.writerow(row)
            

def print_account_info():
    account = boto3.client('sts')
    response = account.get_caller_identity()

    account_id = response.get('Account')
    arn = response.get('Arn')
    user_id = response.get('UserId')

    print(f"Account ID: {account_id}")
    print(f"ARN: {arn}")
    print(f"User ID: {user_id}")

#print_account_info()
client = boto3.client('service-quotas')

# Prompt for the service to query or to search for it
service_code = input("Enter the ServiceCode of the service you want to query (or type 'Search' to find a ServiceCode): ")

if service_code.lower() == "search":
    keyword = input("Enter keyword to search for services: ")
    search_services(client, keyword)
    service_code = input("\nEnter the ServiceCode of the service you want to query: ")

print(f"\nFetching data for {service_code}...")

# Fetch the current quota and AWS defaults using the fetch_all_data function
current_quotas = fetch_all_data(client.list_service_quotas, ServiceCode=service_code)
aws_defaults = fetch_all_data(client.list_aws_default_service_quotas, ServiceCode=service_code)

print(current_quotas)
print(aws_defaults)

# Combine data for CSV
combined_data = []
for current, default in zip(current_quotas, aws_defaults):
    combined_data.append({
        "ServiceCode": service_code,
        "QuotaName": current.get('QuotaName', 'N/A'),
        "CurrentValue": current.get('Value', 'N/A'),
        "AWSDefaultValue": default.get('Value', 'N/A')
    })

# Save to CSV
headers = ["ServiceCode", "QuotaName", "CurrentValue", "AWSDefaultValue"]
save_to_csv("quotas.csv", headers, combined_data)

print("\nData saved to quotas.csv!")
