docker run --rm -it \
  -p 8000:8000 \
  --env-file .env \
  -v ~/.cloudkey/lw-speech-preach-7e812c4fbf18.json:/app/service-account.json \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json \
  practicepreach:dev
