import boto3
import csv

# Initialize the AWS Lambda client
client = boto3.client('lambda')

# Create a CSV file to write the Lambda function information
csv_file = open('lambda_functions.csv', 'w', newline='')
csv_writer = csv.writer(csv_file)

# Write the header row to the CSV file
header = [
    'FunctionName', 'FunctionArn', 'Runtime', 'Role', 'Handler', 'CodeSize',
    'Description', 'Timeout', 'MemorySize', 'LastModified', 'CodeSha256',
    'Version', 'VpcConfig', 'DeadLetterConfig', 'Environment', 'KMSKeyArn'
]
csv_writer.writerow(header)

# Paginate through Lambda functions
next_marker = None
while True:
    if next_marker:
        response = client.list_functions(Marker=next_marker)
    else:
        response = client.list_functions()

    for function in response['Functions']:
        # Extract relevant information from the function
        function_info = [
            function['FunctionName'], function['FunctionArn'],
            function.get('Runtime', ''),  # Check for the existence of 'Runtime'
            function['Role'], function.get('Handler'),
            function['CodeSize'], function['Description'], function['Timeout'],
            function['MemorySize'], function['LastModified'],
            function.get('CodeSha256', ''), function.get('Version', ''),
            function.get('VpcConfig', ''),
            function.get('DeadLetterConfig', ''),
            function.get('Environment', ''),
            function.get('KMSKeyArn', ''),
        ]
        csv_writer.writerow(function_info)

    # Check if there are more functions to retrieve
    if 'NextMarker' in response:
        next_marker = response['NextMarker']
    else:
        break

# Close the CSV file
csv_file.close()

print("Lambda function information exported to lambda_functions.csv")
