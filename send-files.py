import requests
import base64
import os

def upload_file_to_github_repo(content, token):
    url = f"https://api.github.com/repos/DemoNubiral/MX216822-3-claro-cenam-infre-glue/contents/files-folder.tar.gz"
    
    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "message": "Adding tar.gz file",
        "content": content,
    }
    
    response = requests.put(url, json=data, headers=headers)
    
    if response.status_code == 201:
        print(f"File uploaded successfully to MX216822-3-claro-cenam-infre-glue ")
    else:
        print(f"Failed to upload file: {response.json()}")

content = "subiendo archivos al repositorio"
token = os.getenv('TOKEN_ACTIONS')
print(token)


upload_file_to_github_repo(content, token)