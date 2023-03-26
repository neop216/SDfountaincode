SDfountaincode
==================================

Overview
=========

Authors:
Noah Douglass
John Langel
Weiland Moore
Lawrence Ng

Created as a senior design capstone project at Cleveland State University under the guidance of faculty advisor Dr. Sanchita Mal-Sarkar and industry advisor Dr. Rachel Dudukovich of NASA Glenn Research Center.

A fountain code is a type of encoding process that allows the original data to be recovered from sufficiently
large subsets of the encoded data. This property makes them highly desirable in hostile network environments, and thus
perfect for use in space.

https://en.wikipedia.org/wiki/Fountain_code

Arguably the most easily understandable method of encoding blocks involves combining them with the bitwise exclusive-or
operation. This is the foundation of a subclass of fountain codes called Luby transform (LT) codes. The exact methods of
encoding and decoding used by LT codes are fairly standardized and agreed upon, and this software prototype attempts to
implement those methods.

https://en.wikipedia.org/wiki/Luby_transform_code

More advanced and efficient subclasses of fountain code exist, such as Raptor codes, but as most of our research has
been focused on LT fountain codes, the prototype software uses their methodology instead.

Verified Platforms
==================
* Linux
    * Ubuntu 20.04.4 LTS (Focal Fossa) (64-bit)
	* Pop!_OS 22.04 LTS (64-bit)
	* Raspbian 5.15 (32-bit)
	* Raspbian 5.15 (64-bit)
* Windows
    * Windows 10 (64-bit)
	* Windows 11 (64-bit)
	
Requirements
==================
* Python 3.x
	* numpy
	
Usage
=========

## Executability ##
To make the encoder and decoder runnable from the command line, ensure that both scripts are executable.
* On Windows, the scripts will be executable by running them as follows:
	* ```python3 /path/to/encoder```
	* ```python3 /path/to/decoder```
* On Linux, add the executable permission to each file:
	* ```chmod +x /path/to/encoder```
	* ```chmod +x /path/to/decoder```
	
## Encoder Arguments ##
```
encode.py [-h] [-b BYTES] [-r REDUNDANCY] [-tlp TRANSMISSION_LOSS_PERCENTAGE] [--x86] filename
```

* `filename` - Input file path, REQUIRED
* `-h, --help` - Shows this information and exits
* `-b BYTES, --bytes BYTES` - Number of bytes per bundle >= 8
* `-r REDUNDANCY, --redundancy REDUNDNACY` - Scalar for the encoded data's size > 1.0
* `-tlp TRANSMISSION_LOSS_PERCENTAGE, --transmission-loss-percentage TRANSMISSION_LOSS_PERCENTAGE` - Used to simulate transmission loss, 0.0 to 100.0 inclusive
* `--x86` - Forces the use of 32-bit unsigned int datatype for the encoded data buffer for 32-bit systems

## Decoder Arguments ##
```
decode.py [-h] [--x86] filename
```

* `filename` - Input file path, REQUIRED
* `-h, --help` - Shows this information and exits
* `--x86` - Forces the use of 32-bit unsigned int datatype for the encoded data buffer for 32-bit systems
