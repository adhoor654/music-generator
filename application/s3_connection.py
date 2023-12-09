from boto3 import resource

s3 = resource( 's3',
               aws_access_key_id='access key',
               aws_secret_access_key='secret access key' ) 

s3_bucket = s3.Bucket('bucket name')
link_prefix = 'link to bucket root' # files can be accessed with link_prefix + filename