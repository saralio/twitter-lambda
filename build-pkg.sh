#!/bin/sh
rm -rf pkg
rm -f build.zip
mkdir pkg
cp -r bin lib handler.py question.py utils.py requirements.txt pkg/
cd pkg
cd lib 
apt download libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1
cd ..
docker run -v "$PWD":/var/task "lambci/lambda:build-python3.7" /bin/sh -c 'pip install -r requirements.txt -t . --no-cache-dir --compile; exit'
du -hs --apparent-size .
zip -9qr build.zip .
cd ..
cp pkg/build.zip .
du -hs --apparent-size build.zip