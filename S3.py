import boto3
import os

# aws s3 cp /home/gaidica/Documents/NullLink/data/sd2data0.txt s3://neurotechhub-000/

# Initialize the S3 client using the credentials from AWS CLI config
s3 = boto3.client('s3')

# Replace these with your bucket name and the path to the CSV you want to upload
BUCKET_NAME = 'neurotechhub-000'
CSV_DIRECTORY = '/home/gaidica/Documents/NullLink/data/'  # Directory where CSVs are stored

def upload_file_to_s3(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified, file_name is used
    :return: True if file was uploaded, else False
    """
    if object_name is None:
        object_name = file_name

    try:
        s3.upload_file(file_name, bucket, object_name)
        print(f"File '{file_name}' uploaded to '{bucket}/{object_name}'")
        return True
    except Exception as e:
        print(f"Failed to upload {file_name}: {e}")
        return False

def upload_all_files(directory, bucket):
    """Upload all files in a directory to S3"""
    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            file_path = os.path.join(directory, filename)
            upload_file_to_s3(file_path, bucket, filename)

if __name__ == "__main__":
    upload_all_files(CSV_DIRECTORY, BUCKET_NAME)
