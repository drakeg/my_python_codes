import boto3
import csv

def search_services(client, keyword):
  services = fetch_all_data(client.list_services)
  
  matching_services = [s for s in services if keyword.lower() in s['ServiceName'].lower()]

  for service in matching_services:
    print(f"Service Name: {service['ServiceName']} Service Code: {service['ServiceCode']}")

def fetch_all_data(func, **kwargs):
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
  with open(filename, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()
    writer.writerows(data)

def print_account_info():
  account = boto3.client('sts')
  response = account.get_caller_identity()

  account_id = response.get('Account')
  arn = response.get('Arn')
  user_id = response.get('UserId')

  print(f"Account ID: {account_id}")
  print(f"ARN: {arn}")
  print(f"User ID: {user_id}")

client = boto3.client('service-quotas')

service_code = input("Enter ServiceCode to query (or 'Search' to lookup): ")

if service_code.lower() == "search":
  keyword = input("Enter keyword to search: ")
  search_services(client, keyword)
  service_code = input("\nEnter ServiceCode to query: ")

print(f"\nFetching data for {service_code}")

current_quotas = fetch_all_data(client.list_requested_service_quotas, ServiceCode=service_code)
default_quotas = fetch_all_data(client.list_aws_default_service_quotas, ServiceCode=service_code)

combined_data = []
for current in current_quotas:
  default = next((d for d in default_quotas if d['QuotaCode'] == current['QuotaCode']), None)

  row = {
    "ServiceCode": service_code,
    "QuotaName": current['QuotaName'],
    "CurrentValue": current['Value'],  
    "AWSDefaultValue": default['Value'] if default else 'N/A'
  }

  combined_data.append(row)

headers = ["ServiceCode", "QuotaName", "CurrentValue", "AWSDefaultValue"]

save_to_csv("quotas.csv", headers, combined_data)

print("Data saved to quotas.csv")
