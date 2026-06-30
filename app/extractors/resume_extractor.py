import pdfplumber


class ResumeExtractor:

    LINE_TOLERANCE = 3.0
    COLUMN_GAP_THRESHOLD = 25.0

    def extract(self, file_path: str):

        text = ""

        with pdfplumber.open(file_path) as pdf:

            for page in pdf.pages:

                words = page.extract_words(use_text_flow=False)

                if not words:
                    continue

                visual_lines = self._group_words_into_visual_lines(words)

                for vline in visual_lines:
                    text += self._render_visual_line(vline) + "\n"

        return text

    def _group_words_into_visual_lines(self, words):

        visual_lines = []

        for word in sorted(words, key=lambda w: (w['top'], w['x0'])):

            placed = False

            for vline in visual_lines:
                if abs(vline['top'] - word['top']) <= self.LINE_TOLERANCE:
                    vline['words'].append(word)
                    placed = True
                    break

            if not placed:
                visual_lines.append({'top': word['top'], 'words': [word]})

        visual_lines.sort(key=lambda vline: vline['top'])

        return visual_lines

    def _render_visual_line(self, vline) -> str:

        ws = sorted(vline['words'], key=lambda w: w['x0'])

        parts = [ws[0]['text']]

        for prev_w, curr_w in zip(ws, ws[1:]):

            gap = curr_w['x0'] - prev_w['x1']

            if gap > self.COLUMN_GAP_THRESHOLD:
                parts.append('\t')
            else:
                parts.append(' ')

            parts.append(curr_w['text'])

        return ''.join(parts)