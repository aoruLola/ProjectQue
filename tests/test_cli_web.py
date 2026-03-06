from maque.cli import build_parser


def test_build_parser_supports_web_command():
    parser = build_parser()
    args = parser.parse_args(["web", "--host", "127.0.0.1", "--port", "9000"])
    assert args.cmd == "web"
    assert args.host == "127.0.0.1"
    assert args.port == 9000
