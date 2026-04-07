import docx
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.oxml.shared import OxmlElement, qn
import datetime

def add_margin_comment(paragraph, comment_text, author="AI Editor", initials="AE"):
    """
    Adds a native Word comment to the margin of the document for a given paragraph.
    It attaches the comment to the first run in the paragraph (or creates one if none).
    """
    document = paragraph.part.document
    
    # Check if comments part exists
    comments_part = None
    for rel in document.part.rels.values():
        if rel.reltype == 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments':
            comments_part = rel.target_part
            break
            
    if not comments_part:
        from docx.opc.packuri import PackURI
        from docx.opc.part import XmlPart
        
        # XML without xml declaration to avoid lxml parsing error
        comments_xml = f'<w:comments {nsdecls("w")}></w:comments>'
        
        partname = PackURI('/word/comments.xml')
        comments_part = XmlPart(
            partname,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml',
            parse_xml(comments_xml),
            document.part.package
        )
        
        document.part.relate_to(
            comments_part, 
            'http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments'
        )

    # Get comments element
    comments_element = comments_part.element
    
    # 1. Generate unique comment ID
    existing_comments = comments_element.findall('.//w:comment', namespaces={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})
    comment_id = str(len(existing_comments) + 1)
    if existing_comments:
        max_id = max(int(c.get(qn('w:id'), 0)) for c in existing_comments if c.get(qn('w:id')) is not None)
        comment_id = str(max_id + 1)

    # 2. Create the comment element in comments.xml
    def create_element(name): return OxmlElement(name)
    
    comment = create_element('w:comment')
    comment.set(qn('w:id'), comment_id)
    comment.set(qn('w:author'), author)
    if initials:
        comment.set(qn('w:initials'), initials)
    comment.set(qn('w:date'), datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'))

    # Add content to the comment
    p = create_element('w:p')
    lines = comment_text.split('\n')
    for i, line in enumerate(lines):
        r = create_element('w:r')
        t = create_element('w:t')
        t.text = line
        r.append(t)
        p.append(r)
        if i < len(lines) - 1:
            br_r = create_element('w:r')
            br = create_element('w:br')
            br_r.append(br)
            p.append(br_r)
            
    comment.append(p)
    comments_element.append(comment)

    # 3. Bind the comment to the paragraph in the main document
    if not paragraph.runs:
        paragraph.add_run()
        
    first_run = paragraph.runs[0]
    last_run = paragraph.runs[-1]
    
    commentRangeStart = create_element('w:commentRangeStart')
    commentRangeStart.set(qn('w:id'), comment_id)
    commentRangeEnd = create_element('w:commentRangeEnd')
    commentRangeEnd.set(qn('w:id'), comment_id)
    commentReference = create_element('w:commentReference')
    commentReference.set(qn('w:id'), comment_id)

    # Insert RangeStart before the first run
    paragraph._p.insert(paragraph._p.index(first_run._r), commentRangeStart)
    
    # Insert RangeEnd and Reference after the last run
    last_idx = paragraph._p.index(last_run._r)
    paragraph._p.insert(last_idx + 1, commentRangeEnd)
    
    ref_run = create_element('w:r')
    rPr = create_element('w:rPr')
    rStyle = create_element('w:rStyle')
    rStyle.set(qn('w:val'), 'CommentReference')
    rPr.append(rStyle)
    ref_run.append(rPr)
    ref_run.append(commentReference)
    
    paragraph._p.insert(last_idx + 2, ref_run)
    return True

