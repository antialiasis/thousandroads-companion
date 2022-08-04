import bbcode


bbcode_formatter = bbcode.Parser()
bbcode_formatter.add_simple_formatter('spoiler', '<span class="spoiler" title="Click to reveal">%(value)s</span>')


def bbcode_to_html(text):
    return bbcode_formatter.format(text)
