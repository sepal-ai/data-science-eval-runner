import typer

app = typer.Typer()


@app.command()
def hello():
    print("Hello, World!")


@app.command()
def mcp():
    from . import libreoffice_hard2

    libreoffice_hard2.main()


if __name__ == "__main__":
    app()
