# docker-compose-server

A docker-compose config for my personal server.

## Using these files

The easiest way to use these files is to copy the config of a service you want into your own `docker-compose.yaml` file. You'll need to change my domain names to your own.

If you decide to use environment variables, you'll need to create a `.env` file in the same directory as your compose file. This should declare any variables used in the compose file.

For example, if your compose file uses the `CONTAINERS_DIR` and `POSTGRES_PASSWORD` variables I'm using in my compose file, your `.env` file should look something like this:

```
CONTAINERS_DIR=/home/user/my-container-data
POSTGRES_PASSWORD=mysecretpassword
```
