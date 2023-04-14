# mARC

A [matrix](https://matrix.org/) client daemon utilizing static site generation. Inspired by the [mind-blowing speed](https://en.wikipedia.org/wiki/Brown-throated_sloth) and [simplicity](https://github.com/vector-im/element-web/issues) of [Element](https://github.com/vector-im/element-web/issues). 

## Usage
- Rename `.env.example` to `.env` and update the values
- Install dependencies: `pip install -r requirements.txt`
- Run client: `python mitm.py`
- Serve generated files with a http server of choice: `cd www && npx serve`

## Planned features
- Combined room+people list
- One statically generated html file per room
- Usable search
- IRC-convention "edit history" (*fix)
- Flag but never delete messages

## Undecided on
- Reactions

## Features I'm looking forward to not implementing
- Daily notification that tells you to restart the client for an update that does nothing
- Spaces
- Threads
- Video or VoIP
- Historical revisionism (message deletion)