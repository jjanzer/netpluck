import argparse
import sys
import pprint
from enum import Enum
from .netpluck import NetPluck

def main():
	def str2bool(v):
		'''
		Helper to parse bool values
		'''
		if isinstance(v, bool):
			return v
		if v.lower() in ('yes', 'true', 't', 'y', '1'):
			return True
		elif v.lower() in ('no', 'false', 'f', 'n', '0'):
			return False
		else:
			raise argparse.ArgumentTypeError('Boolean value expected.')

	parser = argparse.ArgumentParser(description="Selectively extract files from an archive without reading the entire file")
	parser.add_argument("--path", type=str, help="The input zip file, use 'use b2://' for remote backblaze urls")
	#parser.add_argument("--toc", type=str2bool, nargs="?", help="Print the table of contents file", const=False)
	parser.add_argument("--toc", action="store_true", help="Print the table of contents file")
	parser.add_argument("--filter", type=str, help="If passed will match the regex and output files", default=None)
	parser.add_argument("--flatten", action="store_true", help="If passed will flatten the output files so they do not expand their relative directories from the archive, eg: foo/bar/car.png => output/car.png")
	parser.add_argument("--out", type=str, help="The output folder to write the results to, if no filter is set all files are unpacked", default="output")
	parser.add_argument("--stats", action="store_true", help="Print statistics about the virtual file reads")
	parser.add_argument("--config", type=str, help="Path to the config file for something like backblaze not used for local paths", default='config.zh.json')
	parser.add_argument("--quiet", action="store_true", help="Suppress non-error output")
	args = parser.parse_args()

	in_file = args.path
	print_toc = args.toc
	filter = args.filter
	flatten = args.flatten
	config_path = args.config
	output_dir = args.out
	print_stats = args.stats
	quiet = args.quiet

	np = NetPluck(in_file, config=config_path)
	np.quiet = quiet

	files = np.get_file_list()

	if print_toc:
		for file in files:
			print(file)

	if output_dir:

		if filter != None:
			np.extract_from_filter(filter, output_dir, flatten=flatten)

	if print_stats:
		cached_bytes_str = np.pretty_file_size(np.vf.cached_read_bytes)
		uncached_bytes_str = np.pretty_file_size(np.vf.uncached_read_bytes)
		size_bytes_str = np.pretty_file_size(np.vf.size)

		bytes_saved = np.vf.size - (np.vf.uncached_read_bytes)
		bytes_saved_str = np.pretty_file_size(bytes_saved)
		percent_saved = (bytes_saved / np.vf.size) * 100 if np.vf.size > 0 else 0.0
		percent_saved_str = f"{percent_saved:.2f}%"

		#cached_bytes = np.vf.cached_read_bytes
		print("")
		print(f"File size: {size_bytes_str}")
		print(f"Cache hits: {np.vf.cached_reads} size: {cached_bytes_str}")
		print(f"Uncached reads: {np.vf.uncached_reads} size: {uncached_bytes_str}")
		print(f"Bytes saved: {bytes_saved_str} {percent_saved_str}")

if __name__ == "__main__":
	main()
