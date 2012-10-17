# -*- coding: utf-8 -*-
import io
import os
import struct
from ..pretzel.log import Log

__all__ = ('DICTSource',)
#------------------------------------------------------------------------------#
# DICT Source                                                                           #
#------------------------------------------------------------------------------#
class DICTSource (object):
    """DICT dictionary source
    """
    buffer_size = 1 << 16

    def __init__ (self, datafile, indexfile):
        self.name = os.path.basename (datafile).rpartition ('.') [0]

        self.indexstream = io.open (indexfile, 'rb', buffering = self.buffer_size)
        self.datastream = io.open (datafile, 'rb')

    #--------------------------------------------------------------------------#
    # Validate                                                                 #
    #--------------------------------------------------------------------------#
    @classmethod
    def FromFile (cls, filename):
        """Create source from file if possible
        """
        fileprefix = filename.rpartition ('.') [0]
        filepath = os.path.dirname (filename)

        if filename.lower ().endswith ('.dict'):
            indexfile = (fileprefix + '.idx').lower ()
            for file in os.listdir (filepath or '.'):
                if file.lower () == indexfile:
                    return cls (filename, file)
            Log.Warning ('matching index file was not found: {}'.format (filename))

        elif filename.endswith ('.idx'):
            datafile = (fileprefix + '.dict').lower ()
            for file in os.listdir (filepath or '.'):
                if file.lower () == datafile:
                    return cls (file, filename)
            Log.Warning ('matching data file was not found: {}'.format (filename))

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
        """Source and destination language pair
        """
        return 'Unknown', 'Unknown'

    #--------------------------------------------------------------------------#
    # Cards                                                                    #
    #--------------------------------------------------------------------------#
    def Cards (self, report = None):
        """Iterate over available cards
        """
        desc_struct = struct.Struct ('>2I')
        data = b''
        report = report or (lambda _: None)

        self.indexstream.seek (0, io.SEEK_END)
        index_size = self.indexstream.tell ()
        self.indexstream.seek (0)

        while True:
            report (self.indexstream.tell () / index_size)

            # read chunk
            chunk = self.indexstream.read (self.buffer_size)
            if not chunk:
                break
            data += chunk

            # parse
            start = 0
            while True:

                end = data.find (b'\x00', start)
                if end < 0:
                    break
                word = data [start:end].decode ('utf-8')
                new_start = end + desc_struct.size + 1
                if new_start > len (data):
                    break
                start = new_start
                offset, size = desc_struct.unpack (data [end + 1:start])

                self.datastream.seek (offset)
                body = self.datastream.read (size).decode ('utf-8')

                yield {
                    'words': [word],
                    'body' : {
                        'name': 'root',
                        'children': [{
                            'name' : 'text',
                            'value': body.rstrip ('\n').rstrip ('\r')
                        }]
                    }
                }

            # copy tail
            data = data [start:]

        report (1.)

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Dispose object
        """
        self.indexstream.close ()
        self.datastream.close ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
