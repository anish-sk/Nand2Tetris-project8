import sys, os, glob

ALabelnum = 0

popD = "@SP\nAM=M-1\nD=M\n"
getM = "@SP\nA=M-1\n"
diffTrue = "D=M-D\nM=-1\n"
makeFalse = "@SP\nA=M-1\nM=0\n"
push = "@SP\nA=M\nM=D\n@SP\nM=M+1\n"

arithmetic_operators={
    "sub" : "-",
    "add" : "+",
    "and" : "&",
    "or" : "|",
    "neg" : "-",
    "not" : "!"
}

segment_code={
    "argument" : "ARG",
    "this" : "THIS",
    "that" : "THAT",
    "local" : "LCL",
    "temp" : "5",
    "pointer" : "3",
}
def unary_arithmetic(command):
    operator = arithmetic_operators.get(command[0],command[0]+"not found")
    assign = "M=" + operator + "M\n"
    return getM + assign

def binary_arithmetic(command):
    operator = arithmetic_operators.get(command[0],command[0]+"not found")
    assign = "M=M" + operator + "D\n"
    return popD + getM + assign

def conditional(command):
    global ALabelnum
    name ="ALabel_" + str(ALabelnum)
    if command[0] == "gt":        
        test = "@" + name + "\nD;JGT\n"
    if command[0] == "eq":        
        test = "@" + name + "\nD;JEQ\n"
    if command[0] == "lt":        
        test = "@" + name + "\nD;JLT\n"
    ALabelnum+=1
    label ="(" + name + ")\n"
    return popD + getM + diffTrue + test + makeFalse + label

def pushfunction(command):
    segment = command[1]
    index = command[2]
    if segment == "constant":
        value = "@" + index + "\nD=A\n"
    elif segment == "static":
        value = "@" + fileName + "." + index + "\nD=M\n"
    else:
        if segment == "temp" or segment == "pointer":
            tempp ="A"
        else:
            tempp ="M"
        pointer = segment_code.get(segment, "invalid segment: "+ segment + "\n")
        indexD ="@"+ index +"\nD=A\n"
        valueD ="@"+ pointer +"\nA=" + tempp + "+D\nD=M\n"
        value = indexD + valueD 
    return value + push

def popfunction(command):
    segment = command[1]
    index = command[2]
    if segment == "constant":
        raise Exception("you cannot pop into a constant")
    if segment == "static":
        pointer = "@" + fileName + "." + index + "\n"
        return popD + pointer + "M=D\n"
    if segment == "temp" or segment == "pointer":
        tempp="A"
    else:
        tempp="M"
    pointer = segment_code.get(segment, "invalid segment: "+ segment + "\n")
    indexD = "@" + index + "\nD=A\n"
    addressR13 = "@" + pointer + "\nD=" + tempp + "+D\n@R13\nM=D\n"
    change = "@R13\nA=M\nM=D\n"
    return indexD + addressR13 + popD + change

def programflow(command):
    label=command[1]
    segment=command[0]
    if segment == "label":
        return "(" + label + ")\n"
    elif segment == "goto":
        address="@"+label+"\n"
        jmp="0;JMP\n"
        return address + jmp
    else:
        jmp="@"+label+"\nD;JNE\n"
        return popD + jmp

def functioncall(command): 
    function_name=command[1]
    n=command[2]
    global ALabelnum
    return_address=function_name+str(ALabelnum)+"$RETURN"
    ALabelnum+=1

    part1="@"+return_address+"\nD=A\n"+push
    part2="@LCL\nD=M\n"+push
    part3="@ARG\nD=M\n"+push
    part4="@THIS\nD=M\n"+push
    part5="@THAT\nD=M\n"+push
    part6="@SP\nD=M\n@5\nD=D-A\n@"+n+"\nD=D-A\n"+"@ARG\nM=D\n"
    part7="@SP\nD=M\n@LCL\nM=D\n"
    part8=programflow(["goto",function_name])
    part9="("+return_address+")\n"

    return part1 + part2 + part3 + part4 + part5 + part6 + part7 + part8 + part9

def functiondef(command):
    function_name=command[1]
    num_local=command[2]
    ans="("+function_name+")\n"
    for __ in range(int(num_local)):
        ans+=pushfunction(["push","constant","0"])
    return ans

def functionreturn(command):
    part1="@LCL\nD=M\n@R15\nM=D\n"
    part2="@5\nA=D-A\nD=M\n@R14\nM=D\n"
    part3=popD+"@ARG\nA=M\nM=D\n"
    part4="@ARG\nD=M+1\n@SP\nM=D\n"
    part5="@R15\nD=M-1\nAM=D\nD=M\n@THAT\nM=D\n"
    part5+="@R15\nD=M-1\nAM=D\nD=M\n@THIS\nM=D\n"
    part5+="@R15\nD=M-1\nAM=D\nD=M\n@ARG\nM=D\n"
    part5+="@R15\nD=M-1\nAM=D\nD=M\n@LCL\nM=D\n"
    part5+="@R14\nA=M\n0;JMP\n"    
    
    return part1 + part2 + part3 + part4 + part5

translations ={
    "add": binary_arithmetic,
    "sub": binary_arithmetic,
    "and": binary_arithmetic,
    "or": binary_arithmetic,
    "neg": unary_arithmetic,
    "not": unary_arithmetic,
    "eq": conditional,
    "gt": conditional,
    "lt": conditional,
    "push": pushfunction,
    "pop": popfunction,
    "label": programflow,
    "goto":programflow,
    "if-goto":programflow,
    "call":functioncall,
    "function":functiondef,
    "return":functionreturn
}

def initialize(file):
    file.write("\n///" + file.name + " ///\n")

def translate(line):
    command = line.split('/')[0].strip().split()
    if command == []:
        return ''
    else:
        f = translations.get(command[0], lambda x: "\n//Error: " + command[0] + " not found \n\n")
        return f(command)

def main():
    arg = sys.argv[1]
    global fileName 
    fileName = os.path.basename(arg)[:-3]
    infile = open(arg + ".vm")    
    outfile = open(arg + ".asm", "w")
    initialize(outfile)
    for line in infile:
        outfile.write(translate(line))

def getFiles(files):
    if files.endswith(".vm"): #Then we know it's a single .vm file, not a directory
        return [files]
    else:
        return glob.glob(files + "/*.vm")

if __name__=="__main__":
    main()