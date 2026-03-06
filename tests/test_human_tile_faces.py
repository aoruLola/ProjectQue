from maque.agents.human import HumanAgent


def test_tiao_one_face_differs_from_tiao_five_face():
    one = HumanAgent._tiao_face(1)
    five = HumanAgent._tiao_face(5)
    assert one != five


def test_tiao_five_face_keeps_existing_shape():
    assert HumanAgent._tiao_face(5) == [" | | ", "  |  ", " | | "]
