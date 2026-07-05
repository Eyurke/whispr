from whispr.formatter import FormatOptions, format_text


def opts(**kw):
    base = dict(
        remove_fillers=True,
        capitalize_sentences=True,
        trailing_space=False,
        spoken_commands=False,
        dictionary=(),
        replacements={},
    )
    base.update(kw)
    return FormatOptions(**base)


def test_strips_and_collapses_whitespace():
    assert format_text("  hello   world ", opts()) == "Hello world"


def test_removes_leading_and_middle_fillers():
    out = format_text("Um, hello there, uh, can you hear me?", opts())
    assert out == "Hello there, can you hear me?"


def test_removes_trailing_filler_and_tidies_punctuation():
    assert format_text("that's fine, um.", opts()) == "That's fine."


def test_fillers_inside_words_are_kept():
    out = format_text("the umbrella and the summer hummed", opts())
    assert out == "The umbrella and the summer hummed"


def test_fillers_kept_when_disabled():
    out = format_text("um, hello", opts(remove_fillers=False, capitalize_sentences=False))
    assert out == "um, hello"


def test_capitalizes_sentence_starts():
    out = format_text("hello. how are you? i'm fine", opts())
    assert out == "Hello. How are you? I'm fine"


def test_capitalize_disabled_leaves_case_alone():
    out = format_text("hello. how are you?", opts(capitalize_sentences=False))
    assert out == "hello. how are you?"


def test_capitalize_never_lowercases_existing_text():
    out = format_text("send it to McKinsey. OK?", opts())
    assert out == "Send it to McKinsey. OK?"


def test_trailing_space_appended_when_enabled():
    assert format_text("hello world", opts(trailing_space=True)) == "Hello world "


def test_trailing_space_not_added_to_empty_result():
    assert format_text("   ", opts(trailing_space=True)) == ""


def test_dictionary_enforces_canonical_casing():
    out = format_text(
        "i love wispr flow and github",
        opts(dictionary=("Wispr Flow", "GitHub")),
    )
    assert out == "I love Wispr Flow and GitHub"


def test_replacements_apply_case_insensitively():
    out = format_text(
        "open ai released a model",
        opts(replacements={"open ai": "OpenAI"}),
    )
    assert out == "OpenAI released a model"


def test_spoken_commands_new_line_and_paragraph():
    out = format_text(
        "first line new paragraph second line new line third",
        opts(spoken_commands=True),
    )
    assert out == "First line\n\nSecond line\nThird"


def test_spoken_commands_ignored_when_disabled():
    out = format_text("buy a new line of products", opts())
    assert out == "Buy a new line of products"


def test_space_before_punctuation_removed():
    assert format_text("hello ,world", opts()) == "Hello, world"


def test_comma_inside_numbers_untouched():
    assert format_text("it costs 1,000 dollars", opts()) == "It costs 1,000 dollars"


def test_empty_input_gives_empty_output():
    assert format_text("", opts(trailing_space=True)) == ""


def test_ending_period_added_when_text_ends_bare():
    assert format_text("hello world", opts(ensure_ending_punctuation=True)) == "Hello world."


def test_ending_period_not_added_after_existing_punctuation():
    assert format_text("are you there?", opts(ensure_ending_punctuation=True)) == "Are you there?"


def test_ending_period_respects_trailing_space():
    out = format_text("hello world", opts(ensure_ending_punctuation=True, trailing_space=True))
    assert out == "Hello world. "


def test_ending_period_disabled_leaves_text_bare():
    assert format_text("hello world", opts()) == "Hello world"


def test_ending_period_not_added_to_empty():
    assert format_text("um", opts(ensure_ending_punctuation=True)) == ""
