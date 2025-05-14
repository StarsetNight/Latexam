from Server.apps import api
from Server.core.LatexamServer import LatexamServer


server = LatexamServer()


if __name__ == "__main__":
    server.app.include_router(api)
    server.run()
