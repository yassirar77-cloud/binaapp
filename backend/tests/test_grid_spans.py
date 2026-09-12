"""A grid whose spans do not add up has a hole in it. Report item #5.

The "Suasana" gallery shipped as md:grid-cols-3 with three children spanning
2 + 1 + 1 — four columns of content in a three-column grid. The first row
filled, the second held one small image, and an empty white container sat
beside it.
"""

from app.services.gallery_normalizer import even_out_grid_spans, normalize_gallery_html

BROKEN = (
    '<div class="grid md:grid-cols-3 gap-4">'
    '<div class="md:col-span-2 rounded"><img src="a.jpg" class="object-cover"></div>'
    '<div class="md:col-span-1"><img src="b.jpg" class="object-cover"></div>'
    '<div><img src="c.jpg" class="object-cover"></div>'
    "</div>"
)


class TestUnevenGrids:
    def test_spans_are_dropped_when_they_leave_a_hole(self):
        out = even_out_grid_spans(BROKEN)
        assert "col-span-2" not in out and "col-span-1" not in out

    def test_other_classes_on_the_same_child_survive(self):
        assert 'class="rounded"' in even_out_grid_spans(BROKEN)

    def test_the_images_all_survive(self):
        out = even_out_grid_spans(BROKEN)
        for name in ("a.jpg", "b.jpg", "c.jpg"):
            assert name in out

    def test_a_grid_that_adds_up_is_left_alone(self):
        # 2 + 1 + 1 + 1 + 1 = 6 = two full rows of three.
        balanced = (
            '<div class="grid md:grid-cols-3 gap-4">'
            '<div class="md:col-span-2"><img src="a.jpg"></div>'
            '<div><img src="b.jpg"></div><div><img src="c.jpg"></div>'
            '<div><img src="d.jpg"></div><div><img src="e.jpg"></div>'
            "</div>"
        )
        assert even_out_grid_spans(balanced) == balanced

    def test_a_grid_with_no_spans_at_all_is_left_alone(self):
        plain = (
            '<div class="grid md:grid-cols-3 gap-4">'
            '<div><img src="a.jpg"></div><div><img src="b.jpg"></div>'
            '<div><img src="c.jpg"></div></div>'
        )
        assert even_out_grid_spans(plain) == plain

    def test_nested_grids_are_handled(self):
        nested = (
            '<div class="grid md:grid-cols-2 gap-4">'
            '<div class="md:col-span-1"><div class="grid md:grid-cols-3">'
            '<div class="md:col-span-2"><img src="x.jpg"></div>'
            '<div><img src="y.jpg"></div><div><img src="z.jpg"></div>'
            "</div></div>"
            '<div><img src="w.jpg"></div></div>'
        )
        out = even_out_grid_spans(nested)
        # Inner grid: 2+1+1 = 4 in 3 columns — evened out.
        assert "md:col-span-2" not in out
        # Outer grid: 1 + 1 = 2 in 2 columns — already whole, untouched.
        assert "md:col-span-1" in out

    def test_idempotent(self):
        once = even_out_grid_spans(BROKEN)
        assert even_out_grid_spans(once) == once

    def test_non_grid_markup_is_untouched(self):
        html = '<div class="flex"><div class="col-span-2">x</div></div>'
        assert even_out_grid_spans(html) == html

    def test_it_runs_as_part_of_the_normalizer(self):
        out = normalize_gallery_html(BROKEN)
        assert "col-span-2" not in out

    def test_malformed_markup_never_raises(self):
        assert even_out_grid_spans('<div class="grid grid-cols-3"><div class="col-span-2">') is not None
