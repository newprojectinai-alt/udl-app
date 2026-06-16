
from manim import *

PAYLOAD = '{"title": "UDL Lesson", "scenes": [{"title": "What is Text Representation?", "caption": "Computers process text through representation.", "items": ["Text Representation", "Human Language to Comput", "Understanding Text"], "duration": 6, "animation_type": "ionic_bond"}, {"title": "Layers of Text Representation", "caption": "Multiple layers of text representation.", "items": ["Bit Stream", "Character Encoding", "Presentation", "Syntax"], "duration": 5, "animation_type": "ionic_bond"}, {"title": "Character Encoding: Bits to Characters", "caption": "Bits become characters using encoding.", "items": ["Bits (0s and 1s)", "Character Encoding", "ASCII, Unicode", "Characters (A, b, !, ?)"], "duration": 6, "animation_type": "ionic_bond"}, {"title": "Syntax: Breaking Text into Tokens", "caption": "Tokenization: Text broken into parts.", "items": ["Syntax Layer", "Tokenization", "Tokens (words, punctuati", "\'Hello, world!\' -> \'Hell"], "duration": 6, "animation_type": "ionic_bond"}, {"title": "Subword Tokenization (BPE)", "caption": "Subword tokenization for efficiency.", "items": ["Subword Tokenization", "Byte-Pair Encoding (BPE)", "Breaking down words", "Handling rare words"], "duration": 6, "animation_type": "ionic_bond"}, {"title": "Semantics: Understanding Meaning", "caption": "Representing word meaning numerically.", "items": ["Semantics Layer", "Bag-of-Words (BOW)", "TF-IDF", "Word2Vec, BERT"], "duration": 6, "animation_type": "ionic_bond"}, {"title": "Knowledge Representation and NLP", "caption": "Knowledge graphs and NLP applications.", "items": ["Knowledge Layer", "Entity-Relation Graphs", "Natural Language Process", "Question Answering"], "duration": 6, "animation_type": "ionic_bond"}], "width": 854, "height": 480}'
DATA = __import__("json").loads(PAYLOAD)


class UDLLessonScene(Scene):
    def construct(self):
        self.camera.background_color = "#eef6ff"
        lesson_title = Text(DATA["title"], font_size=30, color=BLUE_E, weight=BOLD).to_edge(UP)
        self.play(FadeIn(lesson_title, shift=DOWN), run_time=0.5)
        for index, scene in enumerate(DATA["scenes"]):
            self.play(*[FadeOut(mob) for mob in self.mobjects if mob is not lesson_title], run_time=0.25)
            self.render_scene(scene, index + 1, len(DATA["scenes"]))
        self.play(FadeOut(*self.mobjects), run_time=0.4)

    def render_scene(self, scene, number, total):
        scene_label = Text(f"Scene {number} of {total}", font_size=20, color=GRAY).to_corner(UL)
        title = Text(scene["title"], font_size=34, color=BLUE_E, weight=BOLD).next_to(scene_label, DOWN, aligned_edge=LEFT)
        caption = Text(scene["caption"], font_size=20, color=DARK_GRAY, line_spacing=0.85).scale_to_fit_width(11).to_edge(DOWN)
        diagram = self.create_diagram(scene).move_to(ORIGIN + UP * 0.15)
        self.play(FadeIn(scene_label), Write(title), run_time=0.7)
        self.play(LaggedStart(*[GrowFromCenter(mob) for mob in diagram], lag_ratio=0.14), run_time=1.4)
        self.play(FadeIn(caption, shift=UP * 0.2), run_time=0.5)
        self.wait(scene.get("duration", 4))

    def create_diagram(self, scene):
        items = scene.get("items") or ["Idea", "Example", "Practice"]
        colors = [BLUE_C, GREEN_C, YELLOW_C, PURPLE_C]
        group = VGroup()
        nodes = VGroup()
        arrows = VGroup()
        spacing = min(3.3, 9 / max(1, len(items)))
        start_x = -spacing * (len(items) - 1) / 2

        for i, item in enumerate(items):
            x = start_x + i * spacing
            shape = Circle(radius=0.82, color=colors[i % len(colors)], fill_color=colors[i % len(colors)], fill_opacity=0.22)
            if i % 2 == 1:
                shape = RoundedRectangle(width=2.0, height=1.35, corner_radius=0.22, color=colors[i % len(colors)], fill_color=colors[i % len(colors)], fill_opacity=0.22)
            label = Text(item, font_size=19, color=BLACK, weight=BOLD).scale_to_fit_width(1.75)
            node = VGroup(shape, label).move_to([x, 0, 0])
            nodes.add(node)
            if i > 0:
                arrows.add(Arrow(nodes[i - 1].get_right(), node.get_left(), buff=0.18, color=BLUE_E, stroke_width=5))

        topic = scene.get("animation_type", "")
        accent = self.topic_accent(topic)
        accent.next_to(nodes, UP, buff=0.55)
        group.add(accent, nodes, arrows)
        return group

    def topic_accent(self, topic):
        if "ionic" in topic or "bond" in topic:
            left = Circle(radius=0.36, color=BLUE, fill_opacity=0.4)
            right = Circle(radius=0.36, color=GREEN, fill_opacity=0.4).shift(RIGHT * 2.2)
            electron = Dot(color=YELLOW).move_to(left.get_right() + RIGHT * 0.25)
            arrow = CurvedArrow(left.get_right(), right.get_left(), color=YELLOW_E)
            label = Text("electron transfer", font_size=18, color=BLUE_E).next_to(arrow, UP)
            return VGroup(left, right, electron, arrow, label)
        if "plant" in topic or "photosynthesis" in topic:
            stem = Line(DOWN * 0.5, UP * 0.45, color=GREEN_E, stroke_width=8)
            leaf1 = Ellipse(width=0.75, height=0.38, color=GREEN, fill_opacity=0.45).shift(LEFT * 0.35 + UP * 0.05).rotate(0.5)
            leaf2 = Ellipse(width=0.75, height=0.38, color=GREEN, fill_opacity=0.45).shift(RIGHT * 0.35 + UP * 0.18).rotate(-0.5)
            sun = Circle(radius=0.25, color=YELLOW, fill_opacity=0.7).shift(LEFT * 1.4 + UP * 0.55)
            return VGroup(sun, stem, leaf1, leaf2)
        return VGroup(Text("Animated concept map", font_size=20, color=BLUE_E), SurroundingRectangle(Text(""), color=BLUE_E, buff=0.1).set_opacity(0))
