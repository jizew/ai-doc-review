import docx
from docx.oxml.shared import OxmlElement, qn
from lxml import etree
import datetime
import difflib

def create_run_element(text, is_del=False, is_ins=False, author="AI Editor", date_str=None, run_id="1"):
    """
    Creates a wrapped w:r inside w:del or w:ins, or just a w:r for unchanged text.
    """
    if not text:
        return None
        
    r = OxmlElement('w:r')
    
    if is_del:
        t = OxmlElement('w:delText')
        t.set(qn('xml:space'), 'preserve')
        t.text = text
        r.append(t)
        
        wrapper = OxmlElement('w:del')
        wrapper.set(qn('w:id'), run_id)
        wrapper.set(qn('w:author'), author)
        if date_str:
            wrapper.set(qn('w:date'), date_str)
        wrapper.append(r)
        return wrapper
        
    elif is_ins:
        t = OxmlElement('w:t')
        t.set(qn('xml:space'), 'preserve')
        t.text = text
        r.append(t)
        
        wrapper = OxmlElement('w:ins')
        wrapper.set(qn('w:id'), run_id)
        wrapper.set(qn('w:author'), author)
        if date_str:
            wrapper.set(qn('w:date'), date_str)
        wrapper.append(r)
        return wrapper
        
    else:
        t = OxmlElement('w:t')
        t.set(qn('xml:space'), 'preserve')
        t.text = text
        r.append(t)
        return r

def _generate_id():
    import random
    return str(random.randint(100000, 999999))

def paragraph_replace_tracked(paragraph, old_text, new_text, author="AI Editor"):
    """
    Replaces old_text with new_text within the paragraph using granular
    track changes (w:del and w:ins) by comparing the exact text differences.
    Returns True on success, False if replacement was refused (e.g. embedded objects).
    """
    p = paragraph._p
    
    # Safety check: refuse to replace if runs contain embedded objects
    # (drawings, OLE equations, shapes) — deleting runs would destroy them
    for run_el in p.findall(qn('w:r')):
        run_xml = etree.tostring(run_el, encoding='unicode')
        if any(tag in run_xml for tag in ['<w:drawing', '<w:object', '<w:pict', 'mc:AlternateContent', '<v:shape']):
            print(f"Warning: paragraph_replace_tracked refused — embedded objects detected. Preserving original.")
            return False

    # Safety check: verify old_text matches actual paragraph text
    # If they differ, we'd be applying changes to the wrong paragraph (index mismatch)
    actual_text = paragraph.text
    old_stripped = old_text.strip()
    actual_stripped = actual_text.strip()
    if old_stripped != actual_stripped:
        # Allow fuzzy match: if old_text is a prefix/suffix of the actual (formula placeholder case)
        # but if they're completely different, refuse
        if not (old_stripped in actual_stripped or actual_stripped in old_stripped or
                len(old_stripped) == 0 or len(actual_stripped) == 0):
            print(f"Warning: paragraph_replace_tracked refused — text mismatch.\n"
                  f"  Expected: {repr(old_stripped[:80])}\n"
                  f"  Actual:   {repr(actual_stripped[:80])}")
            return False

    # 1. Clear existing runs (keep paragraph properties)
    for child in p.xpath('./w:r | ./w:del | ./w:ins | ./w:hyperlink'):
        p.remove(child)
        
    date_str = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # 2. Use difflib to find granular changes between old and new text
    matcher = difflib.SequenceMatcher(None, old_text, new_text)
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            # Unchanged text
            text = old_text[i1:i2]
            el = create_run_element(text, is_del=False, is_ins=False)
            if el is not None:
                p.append(el)
                
        elif tag == 'replace':
            # Deleted part
            del_text = old_text[i1:i2]
            el_del = create_run_element(del_text, is_del=True, is_ins=False, author=author, date_str=date_str, run_id=_generate_id())
            if el_del is not None:
                p.append(el_del)
                
            # Inserted part
            ins_text = new_text[j1:j2]
            el_ins = create_run_element(ins_text, is_del=False, is_ins=True, author=author, date_str=date_str, run_id=_generate_id())
            if el_ins is not None:
                p.append(el_ins)
                
        elif tag == 'delete':
            # Only deleted
            del_text = old_text[i1:i2]
            el_del = create_run_element(del_text, is_del=True, is_ins=False, author=author, date_str=date_str, run_id=_generate_id())
            if el_del is not None:
                p.append(el_del)
                
        elif tag == 'insert':
            # Only inserted
            ins_text = new_text[j1:j2]
            el_ins = create_run_element(ins_text, is_del=False, is_ins=True, author=author, date_str=date_str, run_id=_generate_id())
            if el_ins is not None:
                p.append(el_ins)
                
    return True
