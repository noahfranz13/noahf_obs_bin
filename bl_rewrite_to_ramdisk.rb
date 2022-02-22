#!/usr/bin/env ruby

# Rewrites a BL dataset into guppi_raw format.  This entails 2 things:
#
# 1. Converting header values into expected format (un-stringifying when approprite)
# 2. Removing the padding adter the END keywork of the header section.

$bank = 3.5

def to_fits_ival(s)
  i = Integer(s.gsub("'", '')) rescue 0
  i.inspect.rjust(20).ljust(70)
end

def to_fits_fval(s)
  f = Float(s.gsub("'", '')) rescue 0
  f.inspect.upcase.rjust(20).ljust(70)
end

def fix_obsfreq(s)
  f  = Float(s.gsub("'", '')) rescue 0
  f += 187.5 * (3.5 - $bank)
  f.inspect.upcase.rjust(20).ljust(70)
end

def fix_directio(s)
  # Set DIRECTIO value to 0
  i = 0
  i.inspect.rjust(20).ljust(70)
end

TO_FITS_IVAL = method :to_fits_ival
TO_FITS_FVAL = method :to_fits_fval
FIX_OBSFREQ  = method :fix_obsfreq
FIX_DIRECTIO = method :fix_directio

KW_MAP = {
 'ACC_LEN ' =>  TO_FITS_IVAL, # i
 'BANKNUM ' =>  TO_FITS_IVAL, # i
 'BASE_BW ' =>  TO_FITS_FVAL, # f
 'CAL_DCYC' =>  TO_FITS_FVAL, # f
 'CHAN_BW ' =>  TO_FITS_FVAL, # f
 'CHAN_DM ' =>  TO_FITS_FVAL, # f
 'DATAPORT' =>  TO_FITS_IVAL, # i
 'DIRECTIO' =>  FIX_DIRECTIO, # 0
 'DS_FREQ ' =>  TO_FITS_IVAL, # i
 'DS_TIME ' =>  TO_FITS_IVAL, # i
 'FFTLEN  ' =>  TO_FITS_IVAL, # i
 'NBIN    ' =>  TO_FITS_IVAL, # i
 'NBITS   ' =>  TO_FITS_IVAL, # i
 'NPOL    ' =>  TO_FITS_IVAL, # i
 'OBSBW   ' =>  TO_FITS_FVAL, # f
 'OBSFREQ ' =>  FIX_OBSFREQ,  # fixup
 'OBSNCHAN' =>  TO_FITS_IVAL, # i
 'OFFSET0 ' =>  TO_FITS_FVAL, # f
 'OFFSET1 ' =>  TO_FITS_FVAL, # f
 'OFFSET2 ' =>  TO_FITS_FVAL, # f
 'OFFSET3 ' =>  TO_FITS_FVAL, # f
 'ONLY_I  ' =>  TO_FITS_IVAL, # i
 'OVERLAP ' =>  TO_FITS_IVAL, # i
 'PFB_OVER' =>  TO_FITS_IVAL, # i
 'SCALE0  ' =>  TO_FITS_FVAL, # f
 'SCALE1  ' =>  TO_FITS_FVAL, # f
 'SCALE2  ' =>  TO_FITS_FVAL, # f
 'SCALE3  ' =>  TO_FITS_FVAL, # f
 'SCAN    ' =>  TO_FITS_IVAL, # i
 'SCANLEN ' =>  TO_FITS_FVAL, # f
 'SCANNUM ' =>  TO_FITS_IVAL, # i
 'SCANREM ' =>  TO_FITS_FVAL, # f
 'TBIN    ' =>  TO_FITS_FVAL, # f
 'TFOLD   ' =>  TO_FITS_IVAL  # i
}

def rewrite_header(ifile, ofile)
  blocsize = nil

  ofile.write("BACKEND = 'GUPPI   '".ljust(80))

  while true
    s = ifile.read(80)
    k,v = s.split('= ')

    blocsize = v.to_i if k == 'BLOCSIZE'

    # Map value if keyword requires it
    v = KW_MAP[k][v] if KW_MAP.has_key?(k)

    ofile.write(k)
    break if k.start_with? 'END      '
    ofile.write('= ')
    ofile.write(v)
  end

  return blocsize
end

def rewrite_file(ifilename, ofilename)
  File.open(ifilename, 'r') do |ifile|
    File.open(ofilename, 'w') do |ofile|
      while !ifile.eof?
        print '.'
        blocsize = rewrite_header(ifile, ofile)
        # Skip header padding
        padding = (512 - (ifile.pos % 512)) % 512
        #puts "skipping #{padding} bytes"
        ifile.seek(padding, IO::SEEK_CUR)
        #puts "copying #{blocsize} bytes"
        File.copy_stream(ifile, ofile, blocsize)
        #File.copy_stream(ifile, STDOUT, blocsize)
      end
      puts
    end
  end
  # Delete input file after successful rewrite
  # File.unlink(ifilename)
end

prefix = `hostname`.chomp
$bank = Integer(prefix.sub('blc','')) rescue 3.5
puts "Running on bank #{$bank}"
ARGV.each do |ifilename|
  ofilename = "/mnt/ramdisk/#{prefix}_" + ifilename
  #ofilename = "#{prefix}_" + ifilename
  print "#{ifilename} -> #{ofilename}"
  rewrite_file(ifilename, ofilename)
end
