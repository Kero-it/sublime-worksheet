import sublime
import sublime_plugin
import repl


class WorksheetCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.repl = self.get_repl()
        if self.repl is not None:
            self.remove_previous_results()
            self.view.set_status(
                'worksheet', 'Initialising {0} REPL.'.format(self.language))
            self.repl.correspond('')
            self.process_line(0)

    def get_repl(self):
        settings = sublime.load_settings("worksheet.sublime-settings")
        languages = settings.get('worksheet_languages')
        view_settings = self.view.settings()
        language = view_settings.get('syntax').split('/')[-1].split('.')[0]
        if language in languages:
            self.language = language
            repl_settings = languages.get(language)
            args = repl_settings.get('args')
            del repl_settings['args']
            return repl.Repl(args, **repl_settings)
        else:
            sublime.error_message('No worksheet REPL found for ' + language)

    def remove_previous_results(self):
        view = self.view
        edit = view.begin_edit('remove_previous_results')
        for region in reversed(view.find_all("^" + self.repl.prefix)):
            view.erase(edit, view.full_line(region))
        self.view.end_edit(edit)

    def process_line(self, start):
        view = self.view
        line = view.full_line(start)
        next_start = line.end()
        line_text = view.substr(line)
        is_last_line = "\n" not in line_text
        if is_last_line:                        # this doesn't actually work
            next_start += 1
            line_text += "\n"
        thread = repl.ReplThread(self.repl, line_text)
        self.queue_thread(thread, next_start, is_last_line)
        self.view.set_status(
            'worksheet', 'Sending 1 line to {0} REPL.'.format(self.language))
        thread.start()

    def queue_thread(self, thread, start, is_last_line):
        sublime.set_timeout(
            lambda: self.handle_result(thread, start, is_last_line),
            100
        )

    def handle_result(self, thread, next_start, is_last_line):
        if thread.is_alive():
            self.view.set_status(
                'worksheet', 'Waiting for {0} REPL.'.format(self.language))
            self.queue_thread(thread, next_start, is_last_line)
        else:
            self.view.set_status('worksheet', '')
            edit = self.view.begin_edit('process_line')
            self.view.insert(edit, next_start, thread.result)
            self.view.end_edit(edit)
            next_start += len(thread.result)
            if not is_last_line:
                self.process_line(next_start)
