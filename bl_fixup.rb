#!/usr/bin/env ruby

# Fixes up the headers of a BL dataset IN PLACE (i.e. modifies the input file
# and does NOT make a copy of it) to be fully guppi_raw compatible.
#
# This entails 2 things:
#
# 1. Adding "BACKEND = 'guppi   ' as the first header record (if not already present)
#
# 2. Converting header values into expected format (un-stringifying when approprite)
#
# It does NOT remove padding for DIRECTIO=1 files.  In fact, adding the BACKEND
# record can only be done if the file has DIRECTIO=1 and the headers have at
# least 80 bytes of padding.  Files that lack a BACKEND record and do not meet
# those requirements cannot be processed in-place.
#
# Running this script on an already fixed up file is OK.  Since nothing will
# change, this is effectively a no-op.  NB: This also includes fixing up the
# OBSFREQ value.

# IO stream to which progress indicators should be written
PROGRESS=STDERR

# Load bad_freqs
$LOAD_PATH << File.dirname($0)
require '/home/obs/lib/bad_freqs.rb'

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
  is_freq_bad = BAD_FREQS.index(f)

  # Return `s` unchanged if it has NO  "'" in it AND `f` is NOT in BAD_FREQS.
  return s if s !~ /'/ && !is_freq_bad

  if s =~ /'/
    # Stringified OBSFREQ means it was never fixed up
    f += 187.5 * (3.5 - $bank) # TODO only of f == 1500.0?
    is_freq_bad = BAD_FREQS.index(f)
  end

  if is_freq_bad
    f += 1500.0/512/2
  end

  f.inspect.upcase.rjust(20).ljust(70)
end

TO_FITS_IVAL = method :to_fits_ival
TO_FITS_FVAL = method :to_fits_fval
FIX_OBSFREQ  = method :fix_obsfreq

KW_MAP = {
 'ACC_LEN ' =>  TO_FITS_IVAL, # i
 'BANKNUM ' =>  TO_FITS_IVAL, # i
 'BASE_BW ' =>  TO_FITS_FVAL, # f
 'CAL_DCYC' =>  TO_FITS_FVAL, # f
 'CHAN_BW ' =>  TO_FITS_FVAL, # f
 'CHAN_DM ' =>  TO_FITS_FVAL, # f
 'DATAPORT' =>  TO_FITS_IVAL, # i
 'DIRECTIO' =>  TO_FITS_IVAL, # i
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
} unless defined? KW_MAP

# Rewrite a header.  This works by:
#
# 1. Read in all records of the header
# 2. Seek back to beginning of header
# 3. Validate the BACKEND record already exists OR DIRECTIO==1 and
#    header_length % 512 <= (512-80).
# 4. Reformat in-memory records as needed
# 5. Write out the (possibly reformatted) header records
# 6. Seek past the (possibly reduced by 80 bytes) padding, if directio==1
#
# If successful, this method returns the value of the BLOCSIZE keyword and
# leaves the file pointer is at the start of the data block following the
# header (and any padding).  If validation (step 3) fails, an exception is
# raised and the file poitner will appear unchanged.  For any other
# exceptioins, the file pointer location is unspecified.
def rewrite_header(ifile)
  blocsize = nil
  directio = nil
  has_backend = false
  records = []

  # 1. Read in all records of the header
  while true
    records << ifile.read(80)

    case records[-1]
    when /^BACKEND =/
      has_backend = true
    when /^BLOCSIZE=/
      blocsize = records[-1].split('= ')[1]
      blocsize = blocsize.gsub(/['"]/, '').to_i
    when /^DIRECTIO=/
      directio = records[-1].split('= ')[1]
      directio = (directio.gsub(/['"]/, '').to_i != 0)
    when /^END /
      break
    end
  end

  # 2. Seek back to beginning of header
  ifile.seek(-80*records.length, IO::SEEK_CUR)

  # 3. Validate the BACKEND record already exists -OR- DIRECTIO==1 and
  #    header_length % 512 <= (512-80).
  if !has_backend
    if !directio
      raise 'BACKEND not found and DIRECTIO=0, cannot rewrite in-place'
    end
    if ((80*records.length) % 512) > (512-80)
      raise 'BACKEND not found but insufficient padding to add it, cannot rewrite in-place'
    end
    records.unshift("BACKEND = 'GUPPI   '".ljust(80))
  end

  # 4. Reformat in-memory records as needed
  records.map! do |s|
    # Split record
    k,v = s.split('= ')

    # Map value if keyword requires it
    v = KW_MAP[k][v] if KW_MAP.has_key?(k)

    # Reassemble record (special key-only handling for END record)
    k.start_with?('END ') ? k : k + '= ' + v
  end

  # 5. Write out the (possibly reformatted) header records
  for record in records
    ifile.write(record)
  end

  # 6. Seek past the (possibly reduced by 80 bytes) padding, if directio==1
  if directio
    padding = (512 - (80*records.length)) % 512
    #PROGRESS.puts "skipping #{padding} bytes of padding"
    ifile.seek(padding, IO::SEEK_CUR)
  end

  return blocsize
end

def rewrite_file(ifile)
  while !ifile.eof?
    PROGRESS.print '.'
    blocsize = rewrite_header(ifile)
    #PROGRESS.puts "skipping #{blocsize} bytes of data"
    ifile.seek(blocsize, IO::SEEK_CUR)
  end
  PROGRESS.puts
end

def fixup_argv_files
  # Show help?
  if ARGV.empty? || ARGV.any? {|s| s =~ /^(-h|--help)$/}
    puts "usage: #{File.basename($0)} FILE [...]"
    exit
  end

  # Determine bank (for obs_freq correction)
  prefix = `hostname`.chomp
  $bank = Integer(prefix.sub('blc','')) rescue 3.5
  PROGRESS.puts "Running on bank #{$bank}"

  # Iterate through input files
  ARGV.each do |ifilename|
    File.open(ifilename, 'r+') do |ifile|
      PROGRESS.print "#{ifilename}"
      rewrite_file(ifile)
    end
  end
end

if __FILE__ == $0
  fixup_argv_files
end
