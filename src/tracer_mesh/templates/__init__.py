import jinja2

# init template environment using package loader
env = jinja2.Environment(loader=jinja2.PackageLoader("tracer_mesh", "templates"), autoescape=False)


def load_template(*, name: str) -> jinja2.Template:
    # load template from package resource
    return env.get_template(name)
