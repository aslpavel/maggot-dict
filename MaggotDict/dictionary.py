# -*- coding: utf-8 -*-
import io
import os
import json
import zlib
import itertools

from .sources import Source
from .pretzel.store import FileStore

__all__ = ('Dictionary', 'DictionaryError',)
#------------------------------------------------------------------------------#
# Dictionary                                                                   #
#------------------------------------------------------------------------------#
class DictionaryError (Exception): pass
class Dictionary (object):
    """Maggot dictionary file
    """
    magic = b'mdict::'
    info_name  = b'mdict::info'
    word_index_name = b'mdict::word_index'
    number_index_name = b'mdict::number_index'

    def __init__ (self, filename):
        self.file  = filename
        self.store = FileStore (filename, mode = 'r', offset = len (self.magic))

        # check magic
        if self.magic != self.store.LoadByOffset (0, len (self.magic)):
            raise ValueError ('Invalid file magic: {}'.format (filename))

        # indexes
        self.word_index = DictionaryIndex (self, self.store.Mapping (self.word_index_name),
             lambda key: key.encode ('utf-8') if key else key)
        self.number_index = DictionaryIndex (self, self.store.Mapping (self.number_index_name))

        # info
        info = json.loads (self.store.LoadByName (self.info_name).decode ('utf-8'))
        self.name = info ['name']
        self.size = info ['size']
        self.language = info ['language']

    #--------------------------------------------------------------------------#
    # Factory                                                                  #
    #--------------------------------------------------------------------------#
    @classmethod
    def Compile (cls, src, dst, report = None):
        """Create dictionary from file
        """
        if report:
            report_value = [0]
            def report_changed (value):
                value = round (value, 3)
                if report_value [0] != value:
                    report_value [0] = value
                    report (value)
        else:
            report_changed = lambda _: None

        with open (src, 'rb') as src_stream:
            if src_stream.read (len (cls.magic)) == cls.magic:
                # has already been compiled (just copy)
                src_stream.seek (0, io.SEEK_END)
                src_size, src_offset = float (src_stream.tell ()), 0
                src_stream.seek (0)
                with open (dst, 'wb') as dst_stream:
                    while True:
                        data = src_stream.read (1 << 16)
                        src_offset += len (data)
                        report_changed (src_size / src_offset)
                        if not data:
                            return cls (dst)
                        dst_stream.write (data)

        # compile
        source = Source (src)
        if source is None:
            raise DictionaryError ('Unsupported dictionary format \'{}\''.format (os.path.basename (src)))

        with FileStore (dst, mode = 'n', offset = len (cls.magic)) as store:
            store.SaveByOffset (0, cls.magic)
            card_save = lambda card, desc: store.Save (zlib.compress (json.dumps (card).encode ('utf-8')), desc)
            card_load = lambda desc: json.loads (zlib.decompress (store.Load (desc)).decode ('utf-8'))

            # numerate cards
            words, cards = [], []
            for card in source.Cards (lambda value: report_changed (value / 2.)):
                card ['words'].sort ()
                card_desc = card_save (card, None)
                card_info = card_desc, []
                cards.append (card_info)
                for word in card ['words']:
                    words.append ((word, card_info))
            words.sort ()

            number_next = itertools.count ()
            for word, card_info in words:
                card_info [1].append (next (number_next))

            # create indexes
            word_index = store.Mapping (cls.word_index_name, key_type = 'bytes', value_type = 'struct:>QH')
            number_index = store.Mapping (cls.number_index_name, key_type = 'struct:>I', value_type = 'struct:>QH')

            cards_count, cards_total = 0, len (cards)
            for card_desc, numbers in cards:
                numbers.sort ()
                card = card_load (card_desc)
                card ['numbers'] = numbers
                card_desc = card_save (card,card_desc)

                # word index
                for index, word in enumerate (card ['words']):
                    word_index [word.encode ('utf-8')] = (card_desc, index)

                # number index
                for index, number in enumerate (numbers):
                    number_index [number] = (card_desc, index)

                # report
                cards_count += 1
                report_changed (.5 + cards_count / cards_total)

            report_changed (1)

            # info
            store.SaveByName (cls.info_name, json.dumps ({
                'name'    : source.Name,
                'language': source.Language,
                'size'    : next (number_next),
            }).encode ('utf-8'))

        return cls (dst)

    #--------------------------------------------------------------------------#
    # Indexes                                                                  #
    #--------------------------------------------------------------------------#
    @property
    def ByWord (self):
        """Index by word
        """
        return self.word_index

    @property
    def ByIndex (self):
        """Index by number
        """
        return self.number_index

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    @property
    def Name (self):
        """Dictionary name
        """
        return self.name

    @property
    def Language (self):
        """Language

        Returns language pair "from language", "to language".
        """
        return self.language

    @property
    def Size (self):
        """Size of the dictionary
        """
        return self.size

    @property
    def File (self):
        """Dictionary file name
        """
        return self.file

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def card_load (self, desc):
        """Load card by it's descriptor
        """
        return json.loads (zlib.decompress (self.store.Load (desc)).decode ('utf-8'))

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Dispose dictionary
        """
        self.store.Dispose ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# DictionaryIndex                                                              #
#------------------------------------------------------------------------------#
class DictionaryIndex (object):
    """Dictionary index
    """
    none_entry = (None, None)

    def __init__ (self, dct, index, cast = None):
        self.dct = dct
        self.index = index
        self.cast = cast or (lambda key: key)

    def __getitem__ (self, key):
        if not isinstance (key, slice):
            desc, index = self.index.get (self.cast (key), self.none_entry)
            if not desc:
                return (None, None)

            card = self.dct.card_load (desc)
            return card ['words'][index], card

        else:
            number_start, number_stop = None, None
            try:
                card_desc, word_index = next (self.index [self.cast (key.start):]) [1]
                number_start = self.dct.card_load (card_desc) ['numbers'][word_index]

                card_desc, word_index= next (self.index [self.cast (key.stop):]) [1]
                number_stop  = self.dct.card_load (card_desc) ['numbers'][word_index]
            except StopIteration: pass

            return CardRange (self.dct, number_start, number_stop)

#------------------------------------------------------------------------------#
# Card Range                                                                   #
#------------------------------------------------------------------------------#
class CardRange (object):
    """Card range
    """
    __slots__ = ('dct', 'number_start', 'number_stop')

    def __init__ (self, dct, number_start, number_stop):
        self.dct = dct
        self.number_start = number_start
        self.number_stop = number_stop

    def __iter__ (self):
        """Iterator interface
        """
        if not self.number_start:
            return
        elif not self.number_stop:
            entries = self.dct.number_index.index [self.number_start:]
        else:
            entries = self.dct.number_index.index [self.number_start:self.number_stop]

        for number, entry in entries:
            card = self.dct.card_load (entry [0])
            yield card ['words'][entry [1]], card


    def __len__ (self):
        """Size interface
        """
        if not self.number_stop:
            return 0
        elif not self.number_stop:
            return self.dct.Size () - self.number_start
        else:
            return self.number_stop - self.number_start

# vim: nu ft=python columns=120 :
