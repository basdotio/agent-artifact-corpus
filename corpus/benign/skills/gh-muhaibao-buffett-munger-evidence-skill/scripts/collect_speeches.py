#!/usr/bin/env python3
"""Stage the eleven public Stripe Press Almanack talks; never write a database.

Uses the publisher's visibly linked /book page, retaining its original bytes.
Requires lxml. Initial discovery is recorded in chapter-links.json, from the
rendered publisher cover; no undocumented endpoint or guessed talk URL is used.
Run with --output <staging dir>; --refresh re-downloads the shared source HTML.
Editorial introductions, sidebars, pull quotes and explicit editorial insertions
are staged separately. Later addenda and undated Q&A are separate documents so
they cannot inherit an earlier speech date.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
from lxml import html
from library import download, normalize_metadata

INDEX_URL = 'https://www.stripe.press/poor-charlies-almanack'
BOOK_URL = INDEX_URL + '/book'
WORDS = ['One','Two','Three','Four','Five','Six','Seven','Eight','Nine','Ten','Eleven']
# These anchors are observed publisher text, not inferred speech boundaries.
INTRO_PREFIXES = [
    'In a vow that students the world over',
    'Well known because it was published in',
    'This talk was given in 1996 to the students',
    'In this talk, Charlie explains how he makes decisions',
    'Having ranted in the previous speech',
    'This speech, delivered in October 1998',
    'This speech was delivered in November 2000',
    'This parable and morality play',
    'The editor of this book spent 12 consecutive hours',
    'On a warm late-spring day in 2007',
    'In the run-up to publishing this book',
]
DATES = ['1986-06-13','1994-04-14','1996-04-19','1996-07-20',
         '1998-04-24','1998-10-14','2000-11-10','2000','2003-10-03',
         '2007-05-13','2005']
DATE_ANCHORS = ['June 13, 1986','April 14, 1994','April 19, 1996',
                'July 20, 1996','April 24, 1998','October 14, 1998',
                'November 10, 2000','Summer 2000','October 3, 2003',
                'May 13, 2007','revisions by Charlie in 2005']
REVISION_DATES = {1:'2006', 2:'2006', 3:'2006-03', 5:'2006'}
REVISION_NOTES = {
    1:'The addendum explicitly says As I review in 2006 this talk made in 1986.',
    2:'The addendum explicitly says As I reviewed Talk Two in 2006.',
    3:'The addendum explicitly says As I revisit Talk Three in March 2006.',
    4:'Undated addendum refers retrospectively to the period between 1996 and 2006; no exact composition date asserted.',
    5:'The addendum explicitly says As I review Talk Five in 2006.',
    6:'Undated addendum discusses what has happened by 2006; composition date not independently stated.',
    7:'Undated addendum contains a thought experiment assuming 2006 stock prices; not dated merely from that hypothetical year.',
    8:'Undated addendum recalls composing the fictional account in summer 2000 and later accounting changes.',
    9:'Undated addendum discusses a 2005 book; no precise composition date established.',
    11:'Undated addendum refers to a 2006 book. Publisher text says this talk, made in 2000, despite the chapter header describing a 2005 compilation of 1992/1994/1995 talks. Preserve this inconsistency; do not infer a new 2000 delivery or silently repair it.',
}

def clean(value):
    return re.sub(r'\s+', ' ', value).strip()

def text(node):
    return clean(node.text_content())

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def unique(nodes, match):
    hits = [i for i,n in enumerate(nodes) if match(n)]
    if len(hits) != 1:
        raise ValueError(f'Publisher boundary changed: expected one match, found {hits}')
    return hits[0]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', required=True, type=Path)
    ap.add_argument('--refresh', action='store_true')
    args=ap.parse_args()
    out=args.output.resolve(); out.mkdir(parents=True,exist_ok=True)
    links_path=out/'chapter-links.json'
    if not links_path.exists():
        raise ValueError('Missing observed chapter-links.json; discover links from rendered publisher cover first')
    discovery=json.loads(links_path.read_text())
    if discovery['book_url'] != BOOK_URL or discovery['index_url'] != INDEX_URL:
        raise ValueError('Discovery does not identify the supported publisher source')
    chapter_urls=discovery['chapter_urls']
    if len(chapter_urls)!=11 or len(set(chapter_urls))!=11:
        raise ValueError('Expected eleven actually observed unique chapter links')
    raw_path=out/'book.html'
    if args.refresh or not raw_path.exists():
        raw,mime,final_url=download(BOOK_URL)
        if final_url != BOOK_URL or 'html' not in mime:
            raise ValueError('Unexpected source response')
        raw_path.write_bytes(raw)
    raw=raw_path.read_bytes()
    # Keep an immutable capture even when --refresh replaces the convenience copy.
    raw_path=out/('book-'+hashlib.sha256(raw).hexdigest()[:16]+'.html')
    if not raw_path.exists():
        raw_path.write_bytes(raw)
    root=html.fromstring(raw)
    articles=root.xpath('//article')
    if len(articles)!=1:
        raise ValueError('Expected one complete publisher book article')
    nodes=list(articles[0])
    intro=[unique(nodes,lambda n,p=p:text(n).startswith(p)) for p in INTRO_PREFIXES]
    starts=[unique(nodes,lambda n,w=w:text(n)=='Talk '+w) for w in WORDS]
    end=unique(nodes,lambda n:n.tag=='h2' and text(n)=='Recommended reading')
    bounds=intro+[end]
    manifest={'collection':'Stripe Press public Poor Charlie’s Almanack — eleven talks',
        'collected_at':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
        'index_url':INDEX_URL,'source_url':BOOK_URL,'source_html_path':str(raw_path),
        'source_html_sha256':hashlib.sha256(raw).hexdigest(),
        'source_html_bytes':len(raw),'source_article_blocks':len(nodes),
        'discovery_path':str(links_path),'documents':[],'failures':[],
        'coverage_notes':[
            'Eleven edited publisher talk chapters; not original recordings or a claim to all Munger speeches.',
            'Original talks, dated/undated later addenda, and separately headed undated Q&A receive distinct documents.',
            'Publisher introductions, asides, pull quotes and explicitly identified editorial insertions are secondary companions.',
            'Full publisher HTML is retained; no unverified timecodes or print page numbers are added.',
            'Talk Three is explicitly abridged by the editor. Main speech text preserves short editorial bracket clarifications.',
            'Talk Eight is fiction written in summer 2000. Talk Eleven is a 2005 prepared compilation never delivered as one talk.',
            'Raw source also includes book chapters outside the eleven-talk scope; those are not staged for indexing.'
        ]}

    def save(name,segments,meta):
        if not segments: raise ValueError('Empty document '+name)
        json_path=out/(name+'.json'); meta_path=out/(name+'.metadata.json')
        meta.update(id='stripe-pca-'+name, publisher='Stripe Press',
            edition='Publisher’s public online edition of Poor Charlie’s Almanack; accessed '+manifest['collected_at'][:10],
            publication_date=None, accessed_at=manifest['collected_at'],
            transcript_quality='edited', source_html_path=str(raw_path),
            source_html_sha256=manifest['source_html_sha256'], acquisition_url=BOOK_URL,
            rights='Publisher provides free public web reading. Copyright retained; local research only, no redistribution license inferred.',
            capture_method='Ordinary public server-rendered HTML; lxml extracts visible article blocks. Cover links were observed in rendered browser DOM.',
            locator_notes='Section plus one-based publisher article block number derived from saved HTML; these are extraction locators, not printed pages. No timecodes.',
            paragraph_count=len(segments),
            quality_notes=meta.get('quality_notes',[])+[
                'Edited book version, not guaranteed verbatim recording; quoted examples inside speech are not automatically original Munger sayings.',
                'Whitespace normalized; original punctuation and bracketed name/context clarifications retained. Raw HTML provides full audit trail.',
            'Editorial introductions, sidebars and pull quotes are separately staged as secondary material; explicit editor notes are separated.'
            ])
        normalize_metadata(meta)
        dump(json_path,{'segments':segments}); dump(meta_path,meta)
        manifest['documents'].append({'id':meta['id'],'title':meta['title'],
            'json_path':str(json_path),'metadata_path':str(meta_path),
            'raw_path':str(raw_path),'url':meta['url'],'primary_status':meta['primary_status'],
            'date':meta.get('date'),'paragraphs':len(segments),
            'characters':sum(len(s['text']) for s in segments),
            'coverage':meta['coverage']})

    for j,word in enumerate(WORDS):
        number=j+1; start=starts[j]; stop=bounds[j+1]
        if not (intro[j]<start<stop): raise ValueError('Talk boundary ordering changed')
        title=text(nodes[start+1]); date_line=text(nodes[start+2])
        if DATE_ANCHORS[j] not in date_line: raise ValueError('Date header changed: '+title)
        chapter='Talk '+word
        base={'url':chapter_urls[j],'author':'Charles T. Munger',
              'primary_status':'primary','date':DATES[j],
              'date_precision':{4:'year',7:'month',10:'day'}[len(DATES[j])],
              'date_source_text':date_line,'speaker':'mixed',
              'source_type':'essay' if number in (8,11) else 'speech'}
        notes=[]
        if number==1: notes.append('Harvard School in Los Angeles, now Harvard-Westlake, a prep school; NOT Harvard University. See publisher introduction.')
        if number==3: notes.append('Publisher explicitly states passages were abridged and editorial summaries added. This is the published abridged version, not a complete 1996 transcript.')
        if number==8: notes.append('Fictional morality play composed in summer 2000. The 2003 events and Quant Tech are fictional, as the author explicitly states; never use as factual corporate history.')
        if number==11:
            notes.append('Written/revised by Munger in 2005 as a compilation never delivered as one talk. Based on talks of 1992-02-02, 1994-10-06 and 1995-04-24; do not label whole text as any one original recording.')
            base['underlying_event_dates']=['1992-02-02','1994-10-06','1995-04-24']
        primary=[]; revision=[]; qa=[]; editorial=[]
        mode='main'; heading=chapter+' / '+title+' / '+DATES[j]+' edited text'
        if number==11:
            body_start=unique(nodes,lambda n:n.tag=='h3' and text(n)=='Preface')
        else: body_start=start+3
        for i in range(intro[j],stop):
            n=nodes[i]; value=text(n)
            if not value: continue
            if value==chapter+' Revisited':
                mode='revision'
                heading=value+' / '+(REVISION_DATES.get(number) or 'composition date not established')
                continue
            if value=='Worldly Wisdom, Updated: Q & A with Charlie':
                mode='qa'; heading=value+' / date not established'; continue
            if i==start or i==start+1: continue
            explicit_editorial=(i<body_start or n.tag in {'aside','blockquote'} or
                bool(re.fullmatch(r'\[Charlie .*\]',value)))
            if n.tag.startswith('h') and not explicit_editorial:
                # The numbered subhead and following named tendency both matter.
                heading=chapter+' / '+DATES[j]+' edited text / '+value
                continue
            targets=list(n) if n.tag in {'ul','ol'} else [n]
            for k,item in enumerate(targets,1):
                value=text(item)
                if not value: continue
                locator=f'publisher article block {i+1}'+(f', list item {k}' if n.tag in {'ul','ol'} else '')
                if explicit_editorial:
                    category=('publisher pull quote (may repeat speech)' if n.tag=='blockquote' else
                              'publisher sidebar' if n.tag=='aside' else
                              'publisher introduction/date header/editorial summary')
                    editorial.append({'text':value,'speaker':'unknown',
                        'section':chapter+' / '+category+' / '+locator,
                        'content_role':'editorial','source_block':i+1})
                    continue
                question='csKXZV' in item.get('class','')
                speaker=('Interviewer (unidentified)' if mode=='qa' else 'Audience questioner (unidentified)') if question else 'Charlie Munger'
                # Keep explicit inserted editor notes outside either person's voice.
                pieces=re.split(r'(\[(?:Editor’s note:|The question was garbled,).*?\])',value)
                for piece in pieces:
                    piece=clean(piece)
                    if not piece: continue
                    if re.match(r'\[(?:Editor’s note:|The question was garbled,)',piece):
                        editorial.append({'text':piece,'speaker':'unknown',
                            'section':chapter+' / explicit inline editor note / '+locator,
                            'content_role':'editorial','source_block':i+1})
                    else:
                        seg={'text':piece,'speaker':speaker,'section':heading+' / '+locator,
                             'content_role':'question' if question else 'munger_edited_text',
                             'source_block':i+1}
                        {'main':primary,'revision':revision,'qa':qa}[mode].append(seg)
        key='talk-'+word.lower()
        save(key,primary,dict(base,title=chapter+': '+title,
            coverage='Published main edited text including attributed questions; excludes later addenda, independent Q&A, and editorial material.',quality_notes=notes))
        if revision:
            rdate=REVISION_DATES.get(number)
            save(key+'-revisited',revision,dict(base,title=chapter+' Revisited — '+title,
                date=rdate,date_precision={4:'year',7:'month',10:'day'}[len(rdate)] if rdate else 'unknown',
                date_source_text=REVISION_NOTES[number],source_type='essay',speaker='Charlie Munger',
                parent_work_date=DATES[j],
                coverage='Entire published later Revisited addendum, separately dated; editorial sidebar material excluded.',
                quality_notes=notes+[REVISION_NOTES[number]]))
        if qa:
            save(key+'-updated-qa',qa,dict(base,title='Worldly Wisdom, Updated: Q & A with Charlie',
                date=None,date_precision='unknown',date_source_text='No separate date stated in this Q&A subsection.',
                source_type='interview',speaker='mixed',parent_work_date=DATES[j],
                coverage='Entire independently headed Worldly Wisdom, Updated Q&A; questions separated from Munger answers.',
                quality_notes=['The placement after the 2006 addendum does not establish that these questions were asked in 1994 or 2006.']))
        save(key+'-editorial',editorial,dict(base,title=chapter+': publisher introductions, annotations and pull quotes',
            author='Book editors / publisher; individual authorship not established',speaker='unknown',
            primary_status='secondary',date=None,date_precision='unknown',date_source_text=None,
            source_type='editorial_material',parent_work_date=DATES[j],
            coverage='Publisher introduction, date/version headers, sidebars, pull quotes and identified inserted editor comments; not Munger speech attribution.',
            quality_notes=notes+['A sidebar may quote third parties or repeat Munger. It is editorial evidence, not automatically an independent source or original Munger utterance.']))
    if len([d for d in manifest['documents'] if d['id'].removeprefix('stripe-pca-') in ['talk-'+w.lower() for w in WORDS]])!=11:
        raise ValueError('Incomplete collection')
    manifest['success_count']=len(manifest['documents'])
    manifest['primary_count']=sum(d['primary_status']=='primary' for d in manifest['documents'])
    manifest['secondary_count']=sum(d['primary_status']=='secondary' for d in manifest['documents'])
    dump(out/'manifest.json',manifest)
    print(json.dumps({k:manifest[k] for k in ['success_count','primary_count','secondary_count','failures']},ensure_ascii=False))

if __name__=='__main__':
    main()
