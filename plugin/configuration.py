import mdpopups
import sublime
import sublime_plugin
import webbrowser

from .core.settings import ClientConfig, client_configs
from .core.configurations import (
    get_scope_client_config, config_for_scope, get_default_client_config, clear_window_client_configs
)
from .core.clients import unload_window_clients
from .core.events import Events
from .core.workspace import enable_in_project, disable_in_project


def detect_supportable_view(view: sublime.View):
    config = config_for_scope(view)
    if not config:
        available_config = get_default_client_config(view)
        if available_config:
            show_enable_config(view, available_config)


Events.subscribe("view.on_load_async", detect_supportable_view)
Events.subscribe("view.on_activated_async", detect_supportable_view)


def extract_syntax_name(syntax_file: str) -> str:
    return syntax_file.split('/')[-1].split('.')[0]


def show_enable_config(view: sublime.View, config: ClientConfig):
    syntax = str(view.settings().get("syntax", ""))
    message = "LSP has found a language server for {}. Run \"Setup Language Server\" to start using it".format(
        extract_syntax_name(syntax)
    )
    window = view.window()
    if window:
        window.status_message(message)


def start_view(view: sublime.View):
    view.run_command('lsp_start_client')


class LspEnableLanguageServerGloballyCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()
        available_config = get_scope_client_config(view, client_configs.defaults) or get_default_client_config(view)
        if available_config:
            client_configs.enable(available_config.name)
            clear_window_client_configs(self.window)
            sublime.set_timeout_async(lambda: start_view(view), 500)
            self.window.status_message("{} enabled, starting server...".format(available_config.name))
            return

        self.window.status_message("No config available to enable")


class LspEnableLanguageServerInProjectCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()

        # if no default_config, nothing we can do.
        default_config = get_default_client_config(view)
        if default_config:
            enable_in_project(self.window, default_config.name)
            clear_window_client_configs(self.window)
            sublime.set_timeout_async(lambda: start_view(view), 500)
            self.window.status_message("{} enabled in project, starting server...".format(default_config.name))
        else:
            self.window.status_message("No config available to enable")


class LspDisableLanguageServerGloballyCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()
        global_config = get_scope_client_config(view, client_configs.all)
        if global_config:
            client_configs.disable(global_config.name)
            clear_window_client_configs(self.window)
            sublime.set_timeout_async(lambda: unload_window_clients(self.window.id()), 500)
            self.window.status_message("{} disabled, shutting down server...".format(global_config.name))
            return

        self.window.status_message("No config available to disable")


class LspDisableLanguageServerInProjectCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()
        global_config = get_scope_client_config(view, client_configs.defaults)
        if global_config:
            disable_in_project(self.window, global_config.name)
            clear_window_client_configs(self.window)
            sublime.set_timeout_async(lambda: unload_window_clients(self.window.id()), 500)
            self.window.status_message("{} disabled in project, shutting down server...".format(global_config.name))
            return
        else:
            self.window.status_message("No config available to disable")


supported_syntax_template = '''
Installation steps:

* Open the [LSP documentation](https://lsp.readthedocs.io)
* Read the instructions for {}
* Install the language server on your system
* Choose an option below to start the server

Enable: [Globally](#enable_globally) | [This Project Only](#enable_project)
'''

unsupported_syntax_template = """
*LSP has no built-in configuration for a {} language server*

Visit [langserver.org](https://langserver.org) to find out if a language server exists for this language."""


setup_css = ".mdpopups .lsp_documentation { margin: 20px; font-family: sans-serif; font-size: 1.2rem; line-height: 2}"


class LspSetupLanguageServerCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()
        syntax = view.settings().get("syntax")
        available_config = get_default_client_config(view)

        syntax_name = extract_syntax_name(syntax)
        title = "# Language Server for {}\n".format(syntax_name)

        if available_config:
            content = supported_syntax_template.format(syntax_name)
        else:
            title = "# No Language Server support"
            content = unsupported_syntax_template.format(syntax_name)

        mdpopups.show_popup(
            view,
            "\n".join([title, content]),
            css=setup_css,
            md=True,
            wrapper_class="lsp_documentation",
            max_width=800,
            max_height=600,
            on_navigate=self.on_hover_navigate
        )

    def on_hover_navigate(self, href):
        if href == "#enable_globally":
            self.window.run_command("lsp_enable_language_server_globally")
        elif href == "#enable_project":
            self.window.run_command("lsp_enable_language_server_in_project")
        else:
            webbrowser.open_new_tab(href)
