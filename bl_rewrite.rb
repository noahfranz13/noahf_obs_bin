#!/usr/bin/env ruby

# Rewrites a BL dataset into guppi_raw format.  This entails 3 things:
#
# 1. Adding "BACKEND = 'guppi   ' as the first header record (if not already present)
#  
# 2. Converting header values into expected format (un-stringifying when approprite)
#
# 3. Removing the padding after the END keywork of the header section (and
#    setting DIRECTIO=0 if it was set to 1).
#
# If two arguments are passed and the second is `-` (a hyphen) then the output
# goes to stdout.  If the second argument is not `-` (or not present at all),
# then the output goes to a file that has the same name as the input file plus
# a hostname prefix.

# IO stream to which progress indicators should be written
PROGRESS=STDERR

require 'bl/gbt'

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
  is_freq_bad = BL::GBT::BAD_FREQS.index(f)

  # Return `s` unchanged if it has NO  "'" in it AND `f` is NOT in BAD_FREQS.
  return s if s !~ /'/ && !is_freq_bad

  if s =~ /'/
    # Stringified OBSFREQ means it was never fixed up even for center frequency
    # of the bank.
    f += 187.5 * (3.5 - $bank) # TODO only of f == 1500.0?
    is_freq_bad = BL::GBT::BAD_FREQS.index(f)
  end

  if is_freq_bad
    f += 1500.0/512/2
  end

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

    # Skip any existing BACKEND records
    next if k.start_with?('BACKEND')

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

def rewrite_file(ifile, ofile)
  while !ifile.eof?
    PROGRESS.print '.'
    blocsize = rewrite_header(ifile, ofile)
    # Skip header padding
    padding = (512 - (ifile.pos % 512)) % 512
    #PROGRESS.puts "skipping #{padding} bytes"
    ifile.seek(padding, IO::SEEK_CUR)
    #PROGRESS.puts "copying #{blocsize} bytes"
    File.copy_stream(ifile, ofile, blocsize)
  end
  PROGRESS.puts
end

do_stdout = false
# Special case for outputting to stdout
if ARGV.length ==2 && ARGV[1] == '-'
  ARGV.pop
  do_stdout = true
end

prefix = `hostname`.chomp
$bank = Integer(prefix.sub('blc','')) rescue 3.5
PROGRESS.puts "Running on bank #{$bank}"
ARGV.each do |ifilename|
  File.open(ifilename, 'r') do |ifile|
    if do_stdout
      PROGRESS.print "#{ifilename} -> (stdout)"
      rewrite_file(ifile, STDOUT)
    else
      ofilename = "#{prefix}_" + ifilename
      PROGRESS.print "#{ifilename} -> #{ofilename}"
      File.open(ofilename, 'w') do |ofile|
        rewrite_file(ifile, ofile)
      end
    end
  end
  # Delete input file after successful rewrite (unless outputting to stdout)
  File.unlink(ifilename) unless do_stdout
end
