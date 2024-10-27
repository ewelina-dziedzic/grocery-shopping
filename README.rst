# Deployment

`poetry export -f requirements.txt --output requirements.txt --without-hashes`
`sam build --use-container`
`sam deploy`