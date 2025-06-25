import typer

app = typer.Typer()


@app.command()
def hello():
    print("Hello, World!")


@app.command()
def mcp():
    from . import libreoffice_easy1

    libreoffice_easy1.main()


if __name__ == "__main__":
    app()
