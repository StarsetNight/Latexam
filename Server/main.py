from Server.apps import api
from Server.core.LatexamServer import LatexamServer
from yaml import load, Loader


with open("options.yaml", "r") as f:
    config = load(f, Loader=Loader)
server = LatexamServer(admin_password=config["server"]["admin_pass"])


if __name__ == "__main__":
    server.app.include_router(api)
    server.run(host=config["server"]["host"], port=config["server"]["port"])
