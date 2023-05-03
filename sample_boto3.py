import boto3

# Cognito関連のクライアントを作成
cognito_idp = boto3.client(
    'cognito-idp',
    region_name = 'ap-northeast-1',
)
cognito_identity = boto3.client(
    'cognito-identity',
    region_name = 'ap-northeast-1',
)

# ユーザープールでのサインアップ
def sign_up(username, password, email, nickname):
    response = cognito_idp.sign_up(
        ClientId='3llu2eptq1mpep6dg5q423jnfg',
        Username=username,
        Password=password,
        UserAttributes=[
            {
                'Name': 'email',
                'Value': email
            },
            {
                'Name': 'nickname',
                'Value': nickname
            }
        ]
    )
    return response

# ユーザーの確認
def confirm_sign_up(username, confirmation_code):
    response = cognito_idp.confirm_sign_up(
        ClientId='3llu2eptq1mpep6dg5q423jnfg',
        Username=username,
        ConfirmationCode=confirmation_code,
    )
    return response

# ユーザープールでのログイン (サインイン)
def sign_in(username, password):
    response = cognito_idp.initiate_auth(
        ClientId='3llu2eptq1mpep6dg5q423jnfg',
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': username,
            'PASSWORD': password
        }
    )
    return response['AuthenticationResult']

# 認証情報を使って一時的なAWS認証情報を取得
def get_aws_credentials(id_token, identity_pool_id):
    response = cognito_identity.get_id(
        IdentityPoolId=identity_pool_id,
        Logins={
            'cognito-idp.ap-northeast-1.amazonaws.com/ap-northeast-1_toAqanNIm': id_token
        }
    )
    identity_id = response['IdentityId']

    response = cognito_identity.get_credentials_for_identity(
        IdentityId=identity_id,
        Logins={
            'cognito-idp.ap-northeast-1.amazonaws.com/ap-northeast-1_toAqanNIm': id_token
        }
    )
    return response['Credentials']

# 使用例
username = 'himihiromu@icloud.com'
password = 'cognitoSample_111'
email = 'himihiromu@icloud.com'
nickname = 'your_nickname'

# サインアップ
sign_up(username, password, email, nickname)

confirmation_code = input('confirm')

confirm_sign_up(username, confirmation_code)

# サインイン
auth_result = sign_in(username, password)

# アクセストークン、IDトークン、リフレッシュトークンを取得
access_token = auth_result['AccessToken']
id_token = auth_result['IdToken']
refresh_token = auth_result['RefreshToken']

print(access_token)
print(id_token)
print(refresh_token)

cognito_identity_pool_id = 'ap-northeast-1:bf7a512d-2adf-4943-a1e8-515a95ff7727'

# IDトークンを使用して一時的なAWS認証情報を取得
aws_credentials = get_aws_credentials(id_token, cognito_identity_pool_id)

# AWS認証情報 (アクセスキー、シークレットキー、セッショントークン) を取得
access_key = aws_credentials['AccessKeyId']
secret_key = aws_credentials['SecretKey']
session_token = aws_credentials['SessionToken']


print(access_key)
print(secret_key)
print(session_token)