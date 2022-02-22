#!/usr/bin/env ruby

#require 'filterbank'
require '/home/davidm/local/src/rb-blgbt/lib/filterbank'

f = Filterbank::File.open(ARGV[0], 'r+')

f.read_header do |kw, val, pos|
  case kw
  when 'fch1'
    new_fch1 = val - (f.foff/2)
#    if (new_fch1 == 2574.03515625 || new_fch1 == 2674.03515625)
    if (new_fch1 * 100000000 % 25 == 0)
      puts "Changing fch1 from #{val} to #{new_fch1}"
      f.seek(pos, IO::SEEK_SET)
      f.write([new_fch1].pack('<d'))
    else
      puts "fch1 is: #{val} - already fixed!"
    end
  end
end

f.close
