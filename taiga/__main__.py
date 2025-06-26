import typer

app = typer.Typer()


@app.command()
def hello():
    print("Hello, World!")


@app.command()
def mcp():
    from . import math_in_python

    math_in_python.main()


if __name__ == "__main__":
    app()
